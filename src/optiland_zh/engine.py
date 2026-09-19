"""运行时翻译引擎：在文字进入 Qt 之前把它换掉。

为什么不改源码
--------------
改 ``site-packages`` 里的文件，``pip install -U optiland`` 之后就没了。
这里全部在运行期完成，所以升级不受影响。

关键难点：回译
--------------
GUI 里有 18 处拿控件文字**当逻辑键**用的代码，例如::

    self.on_analysis_type_changed(self.analysisTypeCombo.currentText())

这一句是拿下拉框里显示的文字去查"分析类注册表"。如果把 ``"Spot Diagram"``
翻成 ``"点列图"``，``currentText()`` 就会返回 ``"点列图"``，注册表查不到，
**整个分析功能直接失效**。

所以本引擎不是单向替换，而是双向的：

* 文字**进入** Qt 时英译中（``addItem`` / ``setText`` / ...）
* 原文额外存进控件自己的 ``userData``（自定义角色）
* 逻辑**读出来**时还它英文（``currentText()`` / ``itemText()``）
* ``findText`` / ``setCurrentText`` 这类"按文字查找"的接口，查询词先中译英

这样界面是中文，程序内部看到的仍然是英文，两边都不坏。

用法
----
::

    import optiland_zh
    optiland_zh.install()            # 必须早于 QApplication
    from optiland_gui.run_gui import main
    main()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from .catalog import DEFAULT_LANGUAGE, Catalog, load_catalog

# 存原文用的 Qt 角色号。挑一个大数值，避免和应用自己的 userData 撞车
# （已确认 optiland_gui 全库 0 处使用 setItemData）。
ORIGINAL_ROLE_OFFSET = 0x5A5A


@dataclass
class _State:
    installed: bool = False
    catalog: Catalog | None = None
    # 记录被打过的补丁，便于卸载和测试
    patches: list[tuple[Any, str, Any]] = field(default_factory=list)
    # QTranslator 必须留引用，否则会被 GC 掉，Qt 自带的按钮文字又变回英文
    qt_translator: Any = None


_state = _State()


# ---------------------------------------------------------------------------
# 补丁工具
# ---------------------------------------------------------------------------


def _patch(cls: Any, attr: str, wrapper_factory: Callable[[Any], Any]) -> bool:
    """把 ``cls.attr`` 换掉，并记下原函数以便还原。

    返回是否真的打上了（PySide6 允许给绑定类型赋值，但万一某天不允许，
    这里要能优雅退化而不是整个崩掉）。
    """
    try:
        original = getattr(cls, attr)
    except AttributeError:
        return False
    try:
        setattr(cls, attr, wrapper_factory(original))
    except (TypeError, AttributeError):
        return False
    _state.patches.append((cls, attr, original))
    return True


def _translate_all_str_args(catalog: Catalog) -> Callable[[Any], Any]:
    """包装器：把所有位置参数里的 str 就地翻译。

    对 ``setText`` / ``setWindowTitle`` / ``QMessageBox.information`` 这类
    接口都成立——它们的字符串位置参数都是给人看的文字。

    **不能**用在 ``QComboBox.addItem`` 上：它的第二个参数是 userData，
    可能是程序内部用的字符串，翻了会坏事（那类接口单独处理）。
    """

    def factory(original: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if args:
                args = tuple(
                    catalog.translate(a) if isinstance(a, str) else a for a in args
                )
            return original(self, *args, **kwargs)

        wrapper.__name__ = getattr(original, "__name__", "wrapper")
        wrapper.__doc__ = original.__doc__
        wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
        return wrapper

    return factory


def _translate_str_list_args(catalog: Catalog) -> Callable[[Any], Any]:
    """包装器：翻译"字符串列表"参数，如 ``addItems(list)``。"""

    def factory(original: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if args:
                args = tuple(
                    [catalog.translate(x) for x in a]
                    if isinstance(a, (list, tuple))
                    else a
                    for a in args
                )
            return original(self, *args, **kwargs)

        wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
        return wrapper

    return factory


# ---------------------------------------------------------------------------
# 下拉框：装译文、存原文、回译
# ---------------------------------------------------------------------------


def _combo_add_item(original: Callable[..., Any], catalog: Catalog, role: int) -> Any:
    """``addItem`` / ``insertItem``。

    签名有两种：
        addItem(text, userData=None)
        addItem(icon, text, userData=None)
    所以要先判断第一个位置参数是文字还是图标。
    """

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        args = list(args)

        # 插入型接口第一个参数是位置下标
        offset = 1 if original.__name__.startswith("insert") else 0

        text_at: int | None = None
        if len(args) > offset and isinstance(args[offset], str):
            text_at = offset
        elif len(args) > offset + 1 and isinstance(args[offset + 1], str):
            text_at = offset + 1
        elif "text" in kwargs and isinstance(kwargs["text"], str):
            text_at = -1  # 关键字传入

        if text_at is None:
            return original(self, *args, **kwargs)

        original_text = kwargs["text"] if text_at == -1 else args[text_at]
        translated = catalog.translate(original_text)
        if text_at == -1:
            kwargs["text"] = translated
        else:
            args[text_at] = translated

        result = original(self, *args, **kwargs)

        # 把原文挂到刚插入的那一项上：回译时用它，不依赖反向查表，
        # 所以"多个英文译成同一句中文"也不会串味。
        try:
            if original.__name__.startswith("insert") and args and isinstance(args[0], int):
                index = args[0]
            else:
                index = self.count() - 1
            if index >= 0:
                self.setItemData(index, original_text, role)
        except Exception:
            pass  # 存不上就退化成"只显示中文"，不影响主流程

        return result

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


def _combo_add_items(original: Callable[..., Any], catalog: Catalog, role: int) -> Any:
    """``addItems``：逐条翻，逐条存原文。"""

    def wrapper(self: Any, texts: Iterable[str], *args: Any, **kwargs: Any) -> Any:
        for text in list(texts):
            self.addItem(text)
        return None

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


def _combo_set_item_text(original: Callable[..., Any], catalog: Catalog, role: int) -> Any:
    def wrapper(self: Any, index: int, text: str, *args: Any, **kwargs: Any) -> Any:
        original_text = text
        result = original(self, index, catalog.translate(text), *args, **kwargs)
        try:
            self.setItemData(index, original_text, role)
        except Exception:
            pass
        return result

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


def _combo_read_original(original: Callable[..., Any], role: int) -> Any:
    """``currentText``：把原文还给程序内部。

    这是整个方案能成立的关键一步——界面显示中文，逻辑读到英文。

    注意：**故意不包装 ``itemText``**。Qt 用 ``itemText`` 去渲染下拉列表，
    回译了列表就会显示英文；而且全库只有一处调用 ``itemText``，
    是把它喂给 ``setCurrentText``，那条路径本身就是通的。
    """

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        raw = original(self, *args, **kwargs)
        try:
            index = self.currentIndex()
            if index < 0:
                return raw
            stored = self.itemData(index, role)
            if not isinstance(stored, str):
                return raw
            # 可编辑下拉框：用户手打的文字不该被换成选项原文
            if self.isEditable():
                line = self.lineEdit()
                if line is not None and line.text() != raw:
                    return raw
            return stored
        except Exception:
            return raw

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


def _combo_lookup(original: Callable[..., Any], catalog: Catalog, arg_at: int) -> Any:
    """``findText`` / ``setCurrentText``：查询词先中译英再查。"""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        args = list(args)
        if len(args) > arg_at and isinstance(args[arg_at], str):
            args[arg_at] = catalog.translate(args[arg_at])
        return original(self, *args, **kwargs)

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


# ---------------------------------------------------------------------------
# 输入框：同样需要回译
# ---------------------------------------------------------------------------

# 把原文/译文挂成 Qt 动态属性（Qt 属性系统比 Python 侧字典更稳：
# 控件销毁时自动消失，不用自己管生命周期）
_LE_ORIGINAL = "_optiland_zh_original"
_LE_TRANSLATED = "_optiland_zh_translated"


def _lineedit_set_text(original: Callable[..., Any], catalog: Catalog) -> Any:
    """``QLineEdit.setText``：显示译文，同时记住原文。

    **这个回译是必须的，不是可选优化。** GUI 里有 7 处把 ``.text()`` 读进
    逻辑，其中最要命的是面型编辑框::

        new_type = self.type_edit.text()                          # lens_editor.py:205
        if new_type.lower().strip() in get_available_surface_types():

    后面拿的是**英文**面型表。只做单向翻译的话，``"标准" in
    ["standard", ...]`` 是 False，面型修改会静默失效。
    """

    def wrapper(self: Any, text: Any) -> Any:
        if not isinstance(text, str):
            return original(self, text)
        translated = catalog.translate(text)
        result = original(self, translated)
        try:
            if translated != text:
                self.setProperty(_LE_ORIGINAL, text)
                self.setProperty(_LE_TRANSLATED, translated)
            else:
                self.setProperty(_LE_ORIGINAL, None)
                self.setProperty(_LE_TRANSLATED, None)
        except Exception:
            pass
        return result

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


def _lineedit_text(original: Callable[..., Any]) -> Any:
    """``QLineEdit.text``：内容还是我们写进去的译文时，还原成原文。

    用户手工改过内容（``raw != translated``）就如实返回，不会被误换。
    """

    def wrapper(self: Any) -> Any:
        raw = original(self)
        try:
            stored_original = self.property(_LE_ORIGINAL)
            stored_translated = self.property(_LE_TRANSLATED)
            if (
                isinstance(stored_original, str)
                and isinstance(stored_translated, str)
                and raw == stored_translated
            ):
                return stored_original
        except Exception:
            pass
        return raw

    wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
    return wrapper


# ---------------------------------------------------------------------------
# 安装 / 卸载
# ---------------------------------------------------------------------------

# 构造器：第一个字符串位置参数就是显示文字
#
# 判断标准：该类的 ``__init__`` 里有没有"一上来就是标题"的位置参数。
# 只收 parent 不收 title 的（QWidget / QMainWindow / QDialog / QTabWidget）
# 不能列进来——它们第一个参数是父控件，列了也没用（非 str 会被跳过），
# 但列了会让人误以为覆盖到了。
_CONSTRUCTORS: tuple[tuple[str, str], ...] = (
    ("PySide6.QtWidgets", "QLabel"),
    ("PySide6.QtWidgets", "QPushButton"),
    ("PySide6.QtWidgets", "QToolButton"),
    ("PySide6.QtWidgets", "QCheckBox"),
    ("PySide6.QtWidgets", "QRadioButton"),
    ("PySide6.QtWidgets", "QGroupBox"),
    ("PySide6.QtWidgets", "QCommandLinkButton"),
    ("PySide6.QtWidgets", "QTableWidgetItem"),
    ("PySide6.QtWidgets", "QListWidgetItem"),
    ("PySide6.QtWidgets", "QStandardItem"),
    ("PySide6.QtWidgets", "QStandardItem"),
    ("PySide6.QtGui", "QAction"),
    ("PySide6.QtWidgets", "QMenu"),
    ("PySide6.QtWidgets", "QDockWidget"),      # QDockWidget(title, parent)
    ("PySide6.QtWidgets", "QToolBar"),         # QToolBar(title, parent)
    ("PySide6.QtWidgets", "QProgressDialog"),  # (labelText, cancelButtonText, ...)
)

# 普通"设文字"方法：所有 str 位置参数都是给人看的
_TEXT_METHODS: tuple[tuple[str, str], ...] = (
    ("PySide6.QtWidgets", "QLabel.setText"),
    ("PySide6.QtWidgets", "QAbstractButton.setText"),
    ("PySide6.QtWidgets", "QGroupBox.setTitle"),
    ("PySide6.QtWidgets", "QLineEdit.setPlaceholderText"),
    ("PySide6.QtWidgets", "QPlainTextEdit.setPlainText"),
    ("PySide6.QtWidgets", "QTextEdit.setText"),
    ("PySide6.QtWidgets", "QWidget.setWindowTitle"),
    ("PySide6.QtWidgets", "QWidget.setToolTip"),
    ("PySide6.QtWidgets", "QWidget.setStatusTip"),
    ("PySide6.QtWidgets", "QWidget.setWhatsThis"),
    ("PySide6.QtWidgets", "QMenu.addAction"),
    ("PySide6.QtWidgets", "QMenu.addMenu"),
    ("PySide6.QtWidgets", "QMenu.insertAction"),
    ("PySide6.QtWidgets", "QMenu.insertMenu"),
    ("PySide6.QtWidgets", "QMenuBar.addAction"),
    ("PySide6.QtWidgets", "QMenuBar.addMenu"),
    ("PySide6.QtWidgets", "QMenuBar.insertMenu"),
    ("PySide6.QtWidgets", "QToolBar.addAction"),
    ("PySide6.QtWidgets", "QToolBar.setWindowTitle"),
    ("PySide6.QtWidgets", "QTabWidget.addTab"),
    ("PySide6.QtWidgets", "QTabWidget.insertTab"),
    ("PySide6.QtWidgets", "QTabWidget.setTabText"),
    ("PySide6.QtWidgets", "QTabWidget.setTabToolTip"),
    ("PySide6.QtWidgets", "QSplashScreen.showMessage"),
    # QFormLayout.addRow("标签文字", 控件)：那个 QLabel 是 Qt 在 C++ 里
    # 顺手建出来的，Python 层根本看不到这次构造。只拦 QLabel 的话，
    # 表单里的标签会全部漏掉——实际漏了 19 个。
    ("PySide6.QtWidgets", "QFormLayout.addRow"),
    ("PySide6.QtWidgets", "QFormLayout.insertRow"),
    ("PySide6.QtWidgets", "QSpinBox.setSuffix"),
    ("PySide6.QtWidgets", "QSpinBox.setPrefix"),
    ("PySide6.QtWidgets", "QSpinBox.setSpecialValueText"),
    ("PySide6.QtWidgets", "QDoubleSpinBox.setSuffix"),
    ("PySide6.QtWidgets", "QDoubleSpinBox.setPrefix"),
    ("PySide6.QtWidgets", "QDoubleSpinBox.setSpecialValueText"),
    ("PySide6.QtGui", "QAction.setText"),
    ("PySide6.QtGui", "QAction.setToolTip"),
    ("PySide6.QtGui", "QAction.setStatusTip"),
    ("PySide6.QtGui", "QAction.setIconText"),
    ("PySide6.QtGui", "QAction.setWhatsThis"),
)

# 参数是"字符串列表"的方法
_LIST_METHODS: tuple[tuple[str, str], ...] = (
    ("PySide6.QtWidgets", "QTableWidget.setHorizontalHeaderLabels"),
    ("PySide6.QtWidgets", "QTableWidget.setVerticalHeaderLabels"),
    ("PySide6.QtWidgets", "QTableView.setHorizontalHeaderLabels"),
    ("PySide6.QtWidgets", "QListWidget.addItems"),
    ("PySide6.QtWidgets", "QTreeWidget.setHeaderLabels"),
)

# 静态对话框：所有 str 参数都是标题/正文/过滤器
_DIALOG_STATICS: tuple[tuple[str, str], ...] = (
    ("PySide6.QtWidgets", "QMessageBox.information"),
    ("PySide6.QtWidgets", "QMessageBox.warning"),
    ("PySide6.QtWidgets", "QMessageBox.critical"),
    ("PySide6.QtWidgets", "QMessageBox.question"),
    ("PySide6.QtWidgets", "QMessageBox.about"),
    ("PySide6.QtWidgets", "QMessageBox.aboutQt"),
    ("PySide6.QtWidgets", "QFileDialog.getOpenFileName"),
    ("PySide6.QtWidgets", "QFileDialog.getOpenFileNames"),
    ("PySide6.QtWidgets", "QFileDialog.getSaveFileName"),
    ("PySide6.QtWidgets", "QFileDialog.getExistingDirectory"),
    ("PySide6.QtWidgets", "QInputDialog.getText"),
    ("PySide6.QtWidgets", "QInputDialog.getItem"),
    ("PySide6.QtWidgets", "QInputDialog.getMultiLineText"),
)


def _resolve(dotted: str) -> Any:
    """把 ``"PySide6.QtWidgets.QLabel"`` 解析成真正的类/函数。"""
    import importlib

    module_name, _, attr = dotted.rpartition(".")
    module = importlib.import_module(module_name)
    # 支持 "QMessageBox.information" 这种两级名字
    target: Any = module
    for part in attr.split("."):
        target = getattr(target, part)
    return target


def _owner_in(module_name: str, owner_name: str) -> Any:
    """在指定模块里取一个名字，如 ``("PySide6.QtWidgets", "QWidget")``。"""
    import importlib

    return getattr(importlib.import_module(module_name), owner_name)


def _resolve_class(module_name: str, class_name: str) -> tuple[Any, Any]:
    import importlib

    module = importlib.import_module(module_name)
    return module, getattr(module, class_name)


# ---------------------------------------------------------------------------
# Qt 自带文字的汉化
# ---------------------------------------------------------------------------


def _install_qt_translator(language: str, set_locale: bool = True) -> bool:
    """装 Qt 自己的翻译文件。

    我们能替换的只是 Optiland 写死的字符串。但对话框上的 OK / Cancel /
    Open / Save、``QFileDialog`` 的文件类型标签、右键菜单里的剪切复制，
    这些文字是 Qt 内部产生的，只有加载 ``qtbase_zh_CN.qm`` 才会变中文。

    PySide6 自带这些 ``.qm``（在 ``PySide6/translations``），所以不需要
    额外下载任何东西。
    """
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return False

    if set_locale:
        # 上游 run_gui 会强制把 locale 设成英语，这里覆盖回来，
        # 否则日期/数字格式仍按美式走。
        try:
            QLocale.setDefault(QLocale(language))
        except Exception:
            pass  # locale 名字不被识别就跳过，不影响文字替换

    translations_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    translator = QTranslator()
    if not translator.load(f"qtbase_{language}", translations_dir):
        return False

    app.installTranslator(translator)
    # 必须留住引用：QTranslator 一旦被垃圾回收，Qt 文字立刻变回英文
    _state.qt_translator = translator
    return True


def install(
    language: str = DEFAULT_LANGUAGE,
    catalog: Catalog | None = None,
    set_locale: bool = True,
) -> Catalog:
    """装上汉化补丁。返回实际使用的词库。

    应在创建 ``QApplication`` 之前调用；重复调用是安全的（不会叠两层补丁）。

    参数
    ----
    language
        语言代码（内置词库），或 ``.json`` 文件路径（自定义词库）。
    catalog
        直接给一个已载入的 :class:`~optiland_zh.catalog.Catalog`，优先级最高。
    set_locale
        是否顺带把 Qt 的 locale 也切过去。上游会强制设为英语，
        这里覆盖回来，日期/数字格式才跟着中文习惯走。
    """
    if _state.installed:
        assert _state.catalog is not None
        return _state.catalog

    catalog = catalog or load_catalog(language)
    _state.catalog = catalog

    from PySide6.QtCore import Qt

    role = int(Qt.ItemDataRole.UserRole) + ORIGINAL_ROLE_OFFSET

    # --- 构造器 ---
    for module_name, class_name in _CONSTRUCTORS:
        try:
            _, cls = _resolve_class(module_name, class_name)
        except AttributeError:
            # 不同 PySide6 版本里个别类的位置/有无会变（QStandardItem 就在
            # QtGui 而不是 QtWidgets）。少打一个补丁只是那类控件不汉化，
            # 不应该让整个汉化层起不来。
            continue
        _patch(cls, "__init__", _translate_all_str_args(catalog))

    # --- 设文字的方法 ---
    for module_name, spec in _TEXT_METHODS:
        owner_name, _, method = spec.rpartition(".")
        try:
            owner = _owner_in(module_name, owner_name)
        except AttributeError:
            continue
        _patch(owner, method, _translate_all_str_args(catalog))

    # --- 字符串列表 ---
    for module_name, spec in _LIST_METHODS:
        owner_name, _, method = spec.rpartition(".")
        try:
            owner = _owner_in(module_name, owner_name)
        except AttributeError:
            continue
        _patch(owner, method, _translate_str_list_args(catalog))

    # --- 静态对话框 ---
    for module_name, spec in _DIALOG_STATICS:
        owner_name, _, method = spec.rpartition(".")
        try:
            owner = _owner_in(module_name, owner_name)
        except AttributeError:
            continue
        _patch(owner, method, _translate_all_str_args(catalog))

    # --- 下拉框：装译文 / 存原文 / 回译 ---
    from PySide6.QtWidgets import QComboBox

    _patch(QComboBox, "addItem", lambda o: _combo_add_item(o, catalog, role))
    _patch(QComboBox, "insertItem", lambda o: _combo_add_item(o, catalog, role))
    _patch(QComboBox, "setItemText", lambda o: _combo_set_item_text(o, catalog, role))
    _patch(QComboBox, "addItems", lambda o: _combo_add_items(o, catalog, role))
    _patch(QComboBox, "currentText", lambda o: _combo_read_original(o, role))
    _patch(QComboBox, "findText", lambda o: _combo_lookup(o, catalog, 0))
    _patch(QComboBox, "setCurrentText", lambda o: _combo_lookup(o, catalog, 0))

    # --- 输入框：必须回译（面型/几何参数/优化变量都从这里读） ---
    from PySide6.QtWidgets import QLineEdit

    _patch(QLineEdit, "setText", lambda o: _lineedit_set_text(o, catalog))
    _patch(QLineEdit, "text", _lineedit_text)

    # --- 表格/列表控件里的文字载体 ---
    from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

    _patch(
        QTableWidget,
        "setHorizontalHeaderLabels",
        _translate_str_list_args(catalog),
    )
    _patch(QTableWidgetItem, "setText", _translate_all_str_args(catalog))

    _state.installed = True

    # --- Qt 自带文字：等 QApplication 建好之后再装翻译器 ---
    # 上游的入口在自己内部创建 QApplication，我们插不进中间，所以挂在它的
    # __init__ 上：构造完立刻装 QTranslator，此时还没有任何窗口被创建。
    #
    # 注意不要改挂 exec()——PySide6 里 QApplication.exec 是**静态方法**，
    # app.exec() 会把实例当第一个参数传进包装器，转手就报
    # "QApplication.exec() takes no arguments (1 given)"。
    from PySide6.QtWidgets import QApplication

    def _app_init_factory(original: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = original(self, *args, **kwargs)
            _install_qt_translator(language, set_locale)
            return result

        wrapper._optiland_zh_patched = True  # type: ignore[attr-defined]
        return wrapper

    _patch(QApplication, "__init__", _app_init_factory)

    # QApplication 可能已经存在了（比如测试代码、或者宿主自己先建了）。
    # 那样 __init__ 补丁永远等不到触发，Qt 自带文字就还是英文，
    # 所以这里立刻补装一次。
    if QApplication.instance() is not None:
        _install_qt_translator(language, set_locale)

    return catalog


def uninstall() -> None:
    """还原所有补丁（主要给测试用）。"""
    for owner, attr, original in reversed(_state.patches):
        try:
            setattr(owner, attr, original)
        except Exception:
            pass
    _state.patches.clear()
    _state.installed = False
    _state.catalog = None


def is_installed() -> bool:
    return _state.installed


def translate(text: str) -> str:
    """翻译单个字符串。未安装时原样返回。"""
    if _state.catalog is None:
        return text
    return _state.catalog.translate(text)


def current_catalog() -> Catalog | None:
    """当前生效的词库，未安装时为 ``None``。"""
    return _state.catalog
