"""从 optiland_gui 源码里提取"需要翻译的界面文字"。

为什么需要这个工具
------------------
汉化包最大的维护风险是：上游一升级，新增的界面文字就漏译了。
肉眼看 107k 行不现实，所以这里用 AST 把候选字符串扫出来，
翻译者只需要处理"差集"。

难点在哪
--------
不是所有字符串都是给人看的。``setObjectName("AnalysisPanel")`` 里的那个
``"AnalysisPanel"`` 是 Qt 拿来给控件编号的内部标识符，翻译了反而会触发
样式表和查找逻辑失效。所以必须**看上下文**：知道这个字符串是传给哪个
函数/构造器的，才能判断它是不是界面文字。

用法
----
    python -m optiland_zh.extract                    # 写出 strings.json
    python -m optiland_zh.extract --out raw.json
    python -m optiland_zh.extract --include-all      # 连可疑的一起导出
    python -m optiland_zh.extract --diff catalogs/zh_CN.json
                                                     # 只列还没翻译的
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Iterator

# --------------------------------------------------------------------------
# 接口清单：决定一个字符串算不算界面文字
# --------------------------------------------------------------------------

# 这些调用/构造器的字符串参数**一定是**给人看的文字
TEXT_APIS: frozenset[str] = frozenset(
    {
        # 构造器（第一个位置参数是显示文字）
        "QLabel",
        "QPushButton",
        "QToolButton",
        "QCheckBox",
        "QRadioButton",
        "QGroupBox",
        "QAction",
        "QMenu",
        "QTableWidgetItem",
        "QListWidgetItem",
        "QTreeWidgetItem",
        "QStandardItem",
        "QCommandLinkButton",
        # 设文字的方法
        "setText",
        "setWindowTitle",
        "setToolTip",
        "setStatusTip",
        "setWhatsThis",
        "setPlaceholderText",
        "setLabelText",
        "setInformativeText",
        "setDetailedText",
        "setTitle",
        "setSuffix",
        "setPrefix",
        "setSpecialValueText",
        "addItem",
        "addItems",
        "insertItem",
        "setItemText",
        "addTab",
        "insertTab",
        "setTabText",
        "addMenu",
        "insertMenu",
        "addAction",
        "insertAction",
        "setHorizontalHeaderLabels",
        "setVerticalHeaderLabels",
        "setHeaderData",
        "addToolBar",
        "setWindowFilePath",
        # 项目自己的辅助函数：界面文字经过它们传给 Qt。
        # 不加进这个白名单，像 "&Undo" / "Algorithm:" 这种单词项就会被
        # "必须含空格"的启发式规则筛掉。
        #
        # 注意 _create_dock 故意不在名单里：它的签名是
        #     _create_dock(widget, object_name, title)
        # 第二个参数会进 setObjectName()，是内部标识符（如 "LensEditorDock"），
        # 加了白名单就会把它当成界面文字收进来。标题含空格，启发式能捞到。
        "_create_action",
        "_create_label",
        "_create_button",
        "_make_action",
        "_add_action",
        "PaletteCommand",
        "addRow",
        "add_row",
        "notify",
        "add_command",
        "register_command",
    }
)

# 这些调用里的字符串是**内部标识符 / 路径 / 样式**，绝不能翻
INTERNAL_APIS: frozenset[str] = frozenset(
    {
        "setObjectName",
        "objectName",
        "setProperty",
        "property",
        "setStyleSheet",
        "setIcon",
        "setWindowIcon",
        "setShortcut",
        "setFont",
        "setCursor",
        "setLayout",
        "setAlignment",
        "setSizePolicy",
        "open",
        "join",
        "exists",
        "setToolTipDuration",
        "setAccessibleName",  # 无障碍名，翻不翻都行，先排除减少噪音
    }
)

# 这些调用里的字符串是**开发者看的**（日志、调试、控制台），不是界面文字。
# 注意 ``warning`` / ``critical`` / ``error`` 故意不在这里：它们有可能是
# ``QMessageBox.warning(...)``，那是要翻的。真拿不准就留给翻译者判断。
NON_UI_APIS: frozenset[str] = frozenset(
    {
        "print",
        "debug",
        "info",
        "log",
        "logger",
        "exception",
        "warning_",  # 占位，避免和 QMessageBox.warning 混淆
        "traceback",
        "echo",
    }
)

# 动态串（f-string）里的**非界面**内容。翻译它们会造成实际破坏：
#   - Qt 样式表（QSS）：改了样式就崩
#   - objectName 前缀：如 "PageButton_%d"，改了控件查找就失效
#   - 配置键：如 "Layouts/Config%s"，改了就读不到用户设置
#   - 文件名前缀：如 "Untitled-%d"
NON_UI_DYNAMIC: tuple[re.Pattern[str], ...] = (
    re.compile(r"background-color|font-family|border-radius|border-left|font-size"),
    re.compile(r"Q(Widget|TabBar|PushButton|TextEdit|MainWindow|Label)\s*[\{:#]"),
    re.compile(r"^[A-Za-z]+_\x00$"),          # "PageButton_\x00"
    re.compile(r"^[A-Za-z]+\x00[A-Za-z]+$"),  # "MPL\x00Button"
    re.compile(r"^[A-Za-z]+-[A-Za-z]*\x00$"),  # "Untitled-\x00"
    re.compile(r"^[A-Za-z]+/[A-Za-z]+\x00"),  # "Layouts/Config\x00Geometry"
    re.compile(r"^Layouts/"),
)

# 关键字参数名：作为这些关键字传进去的字符串，一律不翻
INTERNAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "objectName",
        "name",
        "id",
        "key",
        "attr",
        "attribute",
        "className",
        "class_name",
        "stylesheet",
        "style",
        "icon",
        "icon_path",
        "path",
        "file",
        "filename",
        "url",
        "color",
        "colour",
        "font",
        "cursor",
        "shortcut",
        "encoding",
        "mode",
        "kind",
        "type",
        "dtype",
        "fmt",
        "format",
        "unit_test",
    }
)

# 明确不是界面文字的形状（任何上下文都要拒绝）
NOT_TEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[\./\\]"),                       # 路径
    re.compile(r"\.(py|json|png|svg|jpg|ico|ui|qss|txt|csv|zmx|seq|len)$", re.I),
    re.compile(r"^[\W\d_]+$"),                      # 纯符号/数字
    re.compile(r"^#"),                              # 颜色值 #RRGGBB
    re.compile(r"::"),                              # Qt 信号名
    re.compile(r"^https?://"),
    re.compile(r"^-?\d+(\.\d+)?(e[-+]?\d+)?$"),     # 纯数字
    re.compile(r"^\{.*\}$"),                        # 纯占位符
    # 快捷键标签：形如 "Ctrl+Q"、"Shift+F5"，是给键盘看的，不是给人看的
    re.compile(r"^(Ctrl|Alt|Shift|Meta)(\+[A-Za-z0-9+]+)+$"),
    re.compile(r"^F\d{1,2}$"),
)

# 只在"启发式模式"下拒绝：单个词看起来像内部标识符。
#
# 关键：**已知界面接口（TEXT_APIS）传进来的要放行**。表头 "Type" / "Radius" /
# "Material"，菜单项 "&Undo" / "Back"，标签页 "Variables"，这些都是单词，
# 形状和 objectName 一样，但确实是给人看的文字。早期版本一刀切拒绝，
# 结果漏掉了 100 多条界面文字。
HEURISTIC_ONLY_REJECT: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[a-z][a-z0-9_]*$"),               # 单个 snake_case 标识符
    re.compile(r"^[A-Z][A-Za-z0-9]*$"),             # 单个 PascalCase 标识符
    re.compile(r"^%[sd]"),                          # printf 残片
)

# 看起来像给人看的：含空格 + 两个以上字母，或含中文，或首字母大写且够长
LOOKS_HUMAN = re.compile(r"[A-Za-z]{2,}\s+[A-Za-z]|[\u4e00-\u9fff]|[A-Z][a-z]{2,}")

# 看起来像**代码**的：这类字符串是塞进编辑器/终端里的示例代码，
# 翻译它会直接把代码改坏，必须排除。
CODE_LIKE: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(import|from|def|class|for|if|elif|while|with|return|try)\s", re.M),
    re.compile(r"\bprint\s*\("),
    re.compile(r"\w+\.\w+\s*\("),          # 方法调用，如 optic.surfaces.add(
    re.compile(r"\n\s{4,}\S"),             # 缩进代码块
    re.compile(r"^\s*(>>>|\.\.\.)"),       # 交互式提示符
    re.compile(r"\bself\.\w+"),
    re.compile(r"=\s*\w+\.\w+"),           # 形如 x = obj.attr
)

# f-string 里的插值表达式，用来把 "Surface {i}" 归一成可写正则的模式
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


@dataclass
class Occurrence:
    """一个字符串出现的位置，方便翻译者去源码里看上下文。"""

    file: str
    line: int
    api: str | None = None


@dataclass
class Report:
    """提取结果。"""

    static: dict[str, list[Occurrence]] = field(default_factory=dict)
    dynamic: dict[str, list[Occurrence]] = field(default_factory=dict)
    skipped_internal: int = 0

    def add_static(self, text: str, occ: Occurrence) -> None:
        self.static.setdefault(text, []).append(occ)

    def add_dynamic(self, pattern: str, occ: Occurrence) -> None:
        self.dynamic.setdefault(pattern, []).append(occ)


# --------------------------------------------------------------------------
# 找源码
# --------------------------------------------------------------------------


def locate_gui_package() -> Path:
    """定位已安装的 optiland_gui 包目录。"""
    try:
        import optiland_gui
    except ImportError as exc:  # pragma: no cover - 环境问题
        raise SystemExit(
            "找不到 optiland_gui。请先在同一个环境里装好它：\n"
            '    pip install "optiland[gui]"'
        ) from exc
    return Path(optiland_gui.__file__).resolve().parent


def gui_version() -> str:
    """尽力读出 optiland 的版本号，写进报告里备查。"""
    for dist in ("optiland", "optiland-gui"):
        try:
            return f"{dist} {metadata.version(dist)}"
        except metadata.PackageNotFoundError:
            continue
    return "unknown"


# --------------------------------------------------------------------------
# AST 遍历：带上下文地收集字符串
# --------------------------------------------------------------------------


class _Collector(ast.NodeVisitor):
    """遍历语法树，记录每个字符串字面量是被谁调用的。"""

    def __init__(self, filename: str, docstrings: set[int] | None = None) -> None:
        self.filename = filename
        # 文档字符串的节点 id —— 它们长得像界面文字，但其实是给开发者看的
        self._docstrings = docstrings or set()
        self.report = Report()
        # 调用栈：进入 Call 时压入函数名，离开时弹出
        self._call_stack: list[str | None] = []
        self._keyword_stack: list[str | None] = []

    # -- 辅助 --------------------------------------------------------------

    @staticmethod
    def _callee_name(node: ast.Call) -> str | None:
        """取出被调用者的名字：foo(...) -> foo，a.b.c(...) -> c。"""
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr
        if isinstance(func, ast.Name):
            return func.id
        return None

    def _current_api(self) -> str | None:
        return self._call_stack[-1] if self._call_stack else None

    # -- 遍历 --------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        self._call_stack.append(self._callee_name(node))
        self.generic_visit(node)
        self._call_stack.pop()

    def visit_keyword(self, node: ast.keyword) -> None:
        self._keyword_stack.append(node.arg)
        self.generic_visit(node)
        self._keyword_stack.pop()

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and id(node) not in self._docstrings:
            self._consider_static(node.value, node.lineno)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """f-string：抽出来当成"动态模式"，用正则匹配。"""
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("\x00")  # 占位，稍后归一成 \x00
        raw = "".join(parts)
        if "\x00" not in raw:
            # 没有插值的 f-string，当普通字面量处理
            self._consider_static(raw, node.lineno)
            return
        if not LOOKS_HUMAN.search(raw.replace("\x00", " ")):
            return
        # 样式表 / objectName / 配置键：翻了会坏事
        if any(p.search(raw) for p in NON_UI_DYNAMIC):
            self.report.skipped_internal += 1
            return
        # 输出成交互式模板而不是正则：翻译者只需要在 JSON 里写
        #   "match": "Field {0}: ({1}, {2})"
        #   "replace": "视场 {0}：({1}, {2})"
        # 比让他们写 (?P<...>.+?) 友好得多，也不容易写错。
        chunks = raw.split("\x00")
        template = "".join(
            chunk + (f"{{{i}}}" if i < len(chunks) - 1 else "")
            for i, chunk in enumerate(chunks)
        )
        self.report.add_dynamic(
            template,
            Occurrence(self.filename, node.lineno, self._current_api()),
        )

    # -- 判定 --------------------------------------------------------------

    def _consider_static(self, text: str, lineno: int) -> None:
        api = self._current_api()
        keyword = self._keyword_stack[-1] if self._keyword_stack else None

        # 内部标识符 / 日志输出：直接记账跳过
        if api in INTERNAL_APIS or api in NON_UI_APIS or keyword in INTERNAL_KEYWORDS:
            self.report.skipped_internal += 1
            return

        if not (2 <= len(text) <= 200):
            return
        if not LOOKS_HUMAN.search(text):
            return
        if any(p.search(text) for p in NOT_TEXT_PATTERNS):
            return
        # 示例代码片段：翻了会破坏代码
        if any(p.search(text) for p in CODE_LIKE):
            self.report.skipped_internal += 1
            return

        # 不是明确已知的界面接口时，只有当字符串本身"长得像界面文字"才收录：
        # 必须含空格（多个词）或含中文。这样能滤掉绝大多数内部常量。
        if api not in TEXT_APIS:
            if not (re.search(r"[A-Za-z]{2,}\s+\S", text) or re.search(r"[\u4e00-\u9fff]", text)):
                self.report.skipped_internal += 1
                return
            if any(p.search(text) for p in HEURISTIC_ONLY_REJECT):
                self.report.skipped_internal += 1
                return

        self.report.add_static(text, Occurrence(self.filename, lineno, api))


def collect_docstrings(tree: ast.AST) -> set[int]:
    """找出所有文档字符串节点的 id。

    文档字符串就是模块/类/函数体里的第一个字符串表达式。它同样会被
    ``ast.walk`` 当成 ``Constant`` 访问到，但它是写给开发者看的，
    翻译它只会制造噪音。
    """
    ids: set[int] = set()
    scopes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, scopes):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            ids.add(id(first.value))
    return ids


def scan_file(path: Path) -> Report:
    """扫单个文件。语法错误的文件会被跳过并给出提示。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        print(f"  [跳过] {path.name}: 语法错误 {exc}", file=sys.stderr)
        return Report()
    collector = _Collector(path.name, collect_docstrings(tree))
    collector.visit(tree)
    return collector.report


def scan_package(package: Path) -> Report:
    """扫整个包，合并结果。"""
    merged = Report()
    for path in sorted(package.rglob("*.py")):
        part = scan_file(path)
        for text, occs in part.static.items():
            merged.static.setdefault(text, []).extend(occs)
        for pattern, occs in part.dynamic.items():
            merged.dynamic.setdefault(pattern, []).extend(occs)
        merged.skipped_internal += part.skipped_internal
    return merged


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------


def report_to_dict(report: Report) -> dict:
    def occ_to_dict(o: Occurrence) -> dict:
        return {"file": o.file, "line": o.line, "api": o.api}

    return {
        "meta": {
            "source": gui_version(),
            "static_count": len(report.static),
            "dynamic_count": len(report.dynamic),
            "skipped_as_internal": report.skipped_internal,
        },
        "static": {
            text: [occ_to_dict(o) for o in occs]
            for text, occs in sorted(report.static.items())
        },
        "dynamic": {
            pattern: [occ_to_dict(o) for o in occs]
            for pattern, occs in sorted(report.dynamic.items())
        },
    }


def load_translated_keys(catalog_path: Path) -> set[str]:
    """读已有词库，拿到"翻译过的"那批 key，用于算差集。

    静态词条在 ``entries`` 里，动态模板在 ``patterns`` 的 ``match`` 字段里，
    两处都要算，否则动态规则会被误报成未翻译。
    """
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    keys = set(data.get("entries", {}))
    for pattern in data.get("patterns", []):
        if isinstance(pattern, dict) and "match" in pattern:
            keys.add(pattern["match"])
    return keys


def _iter_untranslated(report: Report, done: set[str]) -> Iterator[tuple[str, str]]:
    for text in report.static:
        if text not in done:
            yield "static", text
    for pattern in report.dynamic:
        if pattern not in done:
            yield "dynamic", pattern


# --------------------------------------------------------------------------
# 命令行
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m optiland_zh.extract",
        description="从 optiland_gui 源码提取待翻译的界面文字",
    )
    parser.add_argument("--out", default="strings.json", help="输出 JSON 路径")
    parser.add_argument(
        "--diff",
        metavar="CATALOG",
        help="给一个已有词库，只打印还没翻译的条目（按文件分组）",
    )
    parser.add_argument("--include-all", action="store_true", help="保留低置信度候选")
    parser.add_argument("--package", help="手动指定 optiland_gui 目录")
    args = parser.parse_args(argv)

    package = Path(args.package).resolve() if args.package else locate_gui_package()
    print(f"扫描: {package}")
    report = scan_package(package)

    print(f"  静态候选  : {len(report.static)}")
    print(f"  动态模式  : {len(report.dynamic)}")
    print(f"  跳过(内部): {report.skipped_internal}")

    if args.diff:
        done = load_translated_keys(Path(args.diff))
        missing = list(_iter_untranslated(report, done))
        print(f"\n未翻译: {len(missing)} 条（已翻译 {len(done)} 条）")
        by_file: dict[str, list[str]] = {}
        for kind, text in missing:
            occs = (report.static if kind == "static" else report.dynamic)[text]
            by_file.setdefault(occs[0].file, []).append(text)
        for fname in sorted(by_file):
            print(f"\n  ── {fname} ({len(by_file[fname])}) ──")
            for text in sorted(by_file[fname]):
                shown = text if len(text) <= 70 else text[:67] + "..."
                print(f"     {shown}")
        return 0

    payload = report_to_dict(report)
    out = Path(args.out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写出: {out.resolve()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
