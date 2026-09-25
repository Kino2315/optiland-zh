"""离屏构建真实主窗口，把**实际渲染出来的**每一个文字节点和词库比对。

比人眼看截图靠谱：截图只能看到当前可见的那一屏，这个能把整个窗口树
（含未展开的菜单、未激活的标签页）全查一遍，并且精确指出哪些没翻。

用法::

    python -m optiland_zh.audit            # 列出未覆盖的文字
    python -m optiland_zh.audit --all      # 连已翻译的也列出来
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict


def collect_texts(widget) -> list[tuple[str, str, str]]:
    """遍历控件树，取出所有"渲染出来的文字"。

    返回 (来源描述, 取文字的接口, 文本) 三元组。
    """
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QAbstractButton,
        QComboBox,
        QGroupBox,
        QLabel,
        QMenu,
        QTabWidget,
        QTableView,
        QWidget,
    )

    found: list[tuple[str, str, str]] = []

    def add(kind: str, source: str, text: object) -> None:
        if isinstance(text, str) and text.strip():
            found.append((kind, source, text))

    # 注意是 QWidget 而不是 object：findChildren(object) 会把 QLayout
    # 这类没有 toolTip() 的对象也捞进来。
    for w in widget.findChildren(QWidget):
        name = type(w).__name__
        if isinstance(w, QLabel):
            add("QLabel", name, w.text())
        elif isinstance(w, QGroupBox):
            add("QGroupBox", name, w.title())
        elif isinstance(w, QAbstractButton):
            add("Button", name, w.text())
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                add("ComboItem", f"{name}[{i}]", w.itemText(i))
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                add("Tab", f"{name}[{i}]", w.tabText(i))
        elif isinstance(w, QTableView):
            model = w.model()
            if model is not None:
                from PySide6.QtCore import Qt

                for col in range(model.columnCount()):
                    add(
                        "Header",
                        f"{name}.h[{col}]",
                        model.headerData(col, Qt.Orientation.Horizontal),
                    )
                for row in range(model.rowCount()):
                    add(
                        "RowHeader",
                        f"{name}.v[{row}]",
                        model.headerData(row, Qt.Orientation.Vertical),
                    )
        add("ToolTip", name, w.toolTip())
        for action in w.actions():
            add("Action", name, action.text())
            add("ActionTip", name, action.toolTip())

    for menu in widget.findChildren(QMenu):
        add("Menu", type(menu).__name__, menu.title())
        for action in menu.actions():
            add("MenuAction", type(menu).__name__, action.text())

    for action in widget.findChildren(QAction):
        add("Action", type(widget).__name__, action.text())

    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m optiland_zh.audit")
    parser.add_argument("--all", action="store_true", help="连已翻译的也列出来")
    parser.add_argument("--language", default="zh_CN")
    parser.add_argument(
        "--rule",
        choices=[
            "exact-value",
            "cjk-only",
            "cjk-mixed",
            "MISS:patch-not-fired",
            "MISS:still-translatable",
            "MISS:not-translatable",
        ],
        help="只列出某一档判据判出来的节点（用来核查那个百分比可不可信）",
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from .engine import current_catalog, install

    app = QApplication.instance() or QApplication([])
    install(args.language)
    catalog = current_catalog()
    assert catalog is not None

    # 必须在 install 之后再导入主窗口，否则模块级构造的字符串会漏网
    #
    # 关掉 VTK：3D 视图在离屏（offscreen）平台下拿不到 OpenGL 像素格式，
    # 会直接把进程打崩（Windows 上是 0xC0000005 访问违例）。
    # 关掉之后 GUI 自己会走"VTK 不可用"的降级分支，界面文字照样齐全。
    import optiland_gui.viewer_panel as viewer_panel

    viewer_panel.VTK_AVAILABLE = False

    from optiland_gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    app.processEvents()

    entries = collect_texts(window)

    # 判定逻辑要注意：控件上的文字是**已经被补丁翻译过**的，所以拿到的多半
    # 是中文。用中文去查英文键当然查不到——早期版本就栽在这儿，把 1044 个
    # 已经汉化的节点误报成"未覆盖"。
    #
    # 判据分档，强度依次递减。分档计数是为了让百分比**可审查**：
    # 单看"96.8% 已覆盖"没法判断里面有多少水份。
    english_keys = set(catalog.entries)
    translated_values = set(catalog.entries.values())

    def has_cjk(s: str) -> bool:
        return any("\u4e00" <= ch <= "\u9fff" for ch in s)

    def has_latin(s: str) -> bool:
        return any(ch.isascii() and ch.isalpha() for ch in s)

    # 每档判据各判了多少个节点
    by_rule: Counter[str] = Counter()

    missing: dict[str, list[str]] = defaultdict(list)
    covered: list[str] = []
    by_rule_nodes: dict[str, list[str]] = defaultdict(list)
    for kind, source, text in entries:
        if text in translated_values:
            # 最硬：文字正好是词库里某条的译文
            rule = "exact-value"
            covered.append(f"{kind:<10} {source:<34} {text}")
        elif text in english_keys:
            # 词库里有这条，补丁却没生效 —— 真缺口
            missing[kind].append(f"{source:<34} {text}   <- 命中英文键，补丁没生效")
            rule = "MISS:patch-not-fired"
        elif has_cjk(text) and not has_latin(text):
            # 一个拉丁字母都没有 —— 不可能还残留未翻译的英文。这一档是**确定的**，
            # 不是启发式：原界面是英文，渲染出来全是中文，那就是译好了。
            rule = "cjk-only"
            covered.append(f"{kind:<10} {source:<34} {text}")
        elif has_cjk(text):
            # 中英混合：还剩拉丁字母。实测全是 Qt 的快捷键字母（「文件(F)」）
            # 或本来就不该翻的专有名词（「从 CODE V 导入(C)」），不是漏译。
            # 单独计数，--rule 可以逐条查看。
            rule = "cjk-mixed"
            covered.append(f"{kind:<10} {source:<34} {text}")
        elif catalog.translate(text) != text:
            # 还能被动态规则改写 —— 说明是"还没走补丁的英文原文"
            rule = "MISS:still-translatable"
            missing[kind].append(f"{source:<34} {text}")
        else:
            # 既不是译文也不是英文键，也不含中文：多半是数字、objectName、
            # 第三方标识符 —— 本来就不该翻
            rule = "MISS:not-translatable"
            missing[kind].append(f"{source:<34} {text}")
        by_rule[rule] += 1
        by_rule_nodes[rule].append(f"{kind:<10} {source:<34} {text}")

    total = len(entries)
    hit = len(covered)
    print(f"窗口树里的文字节点: {total}")
    print(f"  已覆盖: {hit}  ({hit / total * 100:.1f}%)")
    print(f"  未覆盖: {total - hit}")
    print()
    print("判定分档（已覆盖按强度从高到低，缺口在后）:")
    # 显式的强度序，**不能按数量排**：cjk-only 只有 30 条，按数量会沉到
    # MISS 缺口下面 —— 而它恰恰是最"确定"的一档（无拉丁字母 = 不可能有未译英文）。
    rule_order = [
        "exact-value",
        "cjk-only",
        "cjk-mixed",
        "MISS:not-translatable",
        "MISS:patch-not-fired",
        "MISS:still-translatable",
    ]
    labels = {
        "exact-value": "文字正好等于词库里的某条译文",
        "cjk-only": "无任何拉丁字母 —— 已译完，确定",
        "cjk-mixed": "中英混合：还剩快捷键字母或专有名词，逐条可查",
        "MISS:not-translatable": "本就是数字/objectName/第三方标识符",
        "MISS:patch-not-fired": "词库有译文但补丁没生效（真缺口）",
        "MISS:still-translatable": "仍是英文原文（真缺口）",
    }
    for rule in rule_order:
        count = by_rule.get(rule, 0)
        if count:
            print(f"  {count:>5}  {rule:<26} {labels[rule]}")
    print()

    strict_hit = by_rule["exact-value"]
    if strict_hit != hit:
        print(
            f"严格口径（只认 exact-value，不含 cjk-only / cjk-mixed）: "
            f"{strict_hit} / {total} = {strict_hit / total * 100:.1f}%"
        )
    real_gaps = by_rule["MISS:patch-not-fired"] + by_rule["MISS:still-translatable"]
    print(f"真缺口（补丁没生效 + 仍是英文原文）: {real_gaps}")
    print()

    if args.rule:
        nodes = sorted(set(by_rule_nodes.get(args.rule, [])))
        print(f"=== 判据 {args.rule} 命中的节点（{len(nodes)} 条去重）===")
        for line in nodes:
            print("   ", line)
        return 0

    if args.all:
        print("=== 已覆盖 ===")
        for line in sorted(set(covered)):
            print("   ", line)
        print()

    print("=== 未覆盖（按类型）===")
    for kind in sorted(missing):
        items = sorted(set(missing[kind]))
        print(f"\n-- {kind} ({len(items)}) --")
        for line in items:
            print("   ", line)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
