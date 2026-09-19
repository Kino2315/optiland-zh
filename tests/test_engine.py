"""引擎补丁的单元测试 —— 这部分**需要 PySide6**。

为什么和 test_catalog.py 分开
-----------------------------
之前两者写在同一个文件里，顶部有一行模块级的::

    pytest.importorskip("PySide6")

模块级的 importorskip 一旦命不中，**整个文件**都会被标成 skipped ——
包括那些根本不需要 Qt 的词库校验。

后果很隐蔽：CI 里那个"不装 Qt 的词库体检"任务会显示绿色通过，
实际上一个断言都没跑。**一个永远绿、什么都不检查的 CI 比没有 CI 更糟**，
因为它会让人以为有保障。

拆开之后：
- test_catalog.py  → 纯数据，任何环境都能跑
- test_engine.py   → 需要 Qt，缺了就是 skip（这时的 skip 是诚实的）
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="需要 PySide6（由 optiland[gui] 提供）")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def installed(app):
    import optiland_zh

    optiland_zh.install("zh_CN")
    yield optiland_zh
    optiland_zh.uninstall()


class TestEngine:
    def test_constructors(self, installed) -> None:
        from PySide6.QtWidgets import QDockWidget, QLabel, QPushButton

        assert QLabel("Lens Data Editor").text() == "镜头数据编辑器"
        assert QPushButton("Run Analysis").text() == "运行分析"
        # QDockWidget 曾经不在白名单里，导致 "Script Editor" 一直是英文
        assert QDockWidget("Script Editor").windowTitle() == "脚本编辑器"

    def test_setters(self, installed) -> None:
        from PySide6.QtWidgets import QLabel, QMainWindow

        label = QLabel()
        label.setText("Run Analysis")
        assert label.text() == "运行分析"

        window = QMainWindow()
        window.setWindowTitle("Optiland GUI")
        assert window.windowTitle() == "Optiland 图形界面"

    def test_menu_and_actions(self, installed) -> None:
        from PySide6.QtWidgets import QMainWindow

        window = QMainWindow()
        menu = window.menuBar().addMenu("&File")
        assert menu.title() == "文件(&F)"
        action = menu.addAction("&Open System...")
        assert action.text() == "打开系统(&O)..."

    def test_form_layout_label(self, installed) -> None:
        """addRow 的标签由 Qt 在 C++ 里创建，只拦 QLabel 是抓不到的。"""
        from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

        # 父控件必须留引用：写成 QFormLayout(QWidget()) 的话，那个临时
        # QWidget 立刻被 Python 回收，C++ 侧的 layout 也跟着没了，
        # 报 "Internal C++ object already deleted"。
        host = QWidget()
        form = QFormLayout(host)
        form.addRow("Aperture Type:", QLabel(host))
        label_item = form.itemAt(0, QFormLayout.ItemRole.LabelRole)
        assert label_item.widget().text() == "孔径类型："

    def test_dock_widget_title(self, installed) -> None:
        """QDockWidget 曾经整类漏在白名单外。"""
        from PySide6.QtWidgets import QDockWidget

        assert QDockWidget("Console").windowTitle() == "控制台"

    def test_combo_shows_chinese_but_reads_english(self, installed) -> None:
        from PySide6.QtWidgets import QComboBox

        combo = QComboBox()
        combo.addItem("Spot Diagram")
        combo.addItem("Ray Fan")

        # 界面（Qt 渲染用的 itemText）是中文
        assert combo.itemText(0) == "点列图"
        assert combo.itemText(1) == "光线扇形图"

        # 但程序内部读到的必须是英文，否则注册表查不到
        combo.setCurrentIndex(0)
        assert combo.currentText() == "Spot Diagram"

    def test_combo_findtext_translates_query(self, installed) -> None:
        from PySide6.QtWidgets import QComboBox

        combo = QComboBox()
        combo.addItem("Spot Diagram")
        assert combo.findText("Spot Diagram") == 0

    def test_combo_userdata_does_not_leak_into_logic(self, installed) -> None:
        """原文存在 userData 里，不能被应用自己的 userData 覆盖掉。"""
        from PySide6.QtWidgets import QComboBox

        combo = QComboBox()
        combo.addItem("Spot Diagram", "app-payload")
        combo.setCurrentIndex(0)
        # 应用自己取的 userData 还是它自己放进去的那个
        assert combo.itemData(0) == "app-payload"
        # 而 currentText 仍然回译成英文
        assert combo.currentText() == "Spot Diagram"

    def test_lineedit_roundtrip(self, installed) -> None:
        """面型编辑靠这个：显示中文，读回英文。"""
        from PySide6.QtWidgets import QLineEdit

        edit = QLineEdit()
        edit.setText("Standard")
        assert edit.text() == "Standard"      # 回译
        assert edit.displayText() == "标准"   # 显示的是中文

    def test_lineedit_user_edit_is_not_reversed(self, installed) -> None:
        """用户手打的内容不能被误换成词条原文。"""
        from PySide6.QtWidgets import QLineEdit

        edit = QLineEdit()
        edit.setText("Standard")
        edit.setText("50.0")                  # 模拟用户改成数值
        assert edit.text() == "50.0"

    def test_lineedit_untranslated_passthrough(self, installed) -> None:
        from PySide6.QtWidgets import QLineEdit

        edit = QLineEdit()
        edit.setText("22.0136")
        assert edit.text() == "22.0136"

    def test_untranslated_text_is_untouched(self, installed) -> None:
        """词库命不中的文字必须原样保留，否则界面会出现空白。"""
        from PySide6.QtWidgets import QLabel

        assert QLabel("zzz definitely not in the catalog").text() == (
            "zzz definitely not in the catalog"
        )

    def test_uninstall_restores(self, installed) -> None:
        from PySide6.QtWidgets import QLabel

        installed.uninstall()
        assert QLabel("Lens Data Editor").text() == "Lens Data Editor"
        assert not installed.is_installed()
