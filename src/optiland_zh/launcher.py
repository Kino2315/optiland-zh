"""``optiland-zh`` 启动器：装上汉化，再拉起 Optiland GUI。

用法
----
::

    optiland-zh                          # 启动中文界面
    optiland-zh --list-languages         # 看有哪些语言
    optiland-zh -l zh_TW                 # 换语言（如果有人贡献了词库）
    optiland-zh -c my_catalog.json       # 用自定义词库调试
    optiland-zh --coverage               # 看词库覆盖了多少界面文字
    optiland-zh --self-test              # 不弹窗，自检汉化是否生效
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from typing import Callable

from . import __version__
from .catalog import DEFAULT_LANGUAGE, available_languages, load_catalog

# 本项目用的是哪个上游
UPSTREAM_HINT = 'pip install "optiland[gui]"'


def _require_optiland(
    needs_gui: bool = True,
    finder: Callable[[str], object] | None = None,
) -> None:
    """启动前先确认 Optiland（和 PySide6）装好了。

    为什么需要这个检查
    ------------------
    本项目刻意**不声明** ``optiland`` 依赖 —— 免得和用户已经装好的 Qt
    版本打架。代价是用户很可能只装了汉化包就跑，那时会撞上一个::

        ModuleNotFoundError: No module named 'PySide6'

    这个报错完全看不出"你还需要装 optiland"，所以这里主动换成一句
    能照着做的提示。

    ``needs_gui=False`` 时只要求 PySide6（自检、审计用不到 optiland 本体）。
    ``finder`` 是留出来给测试注入的，默认用 importlib。
    """
    find = finder or importlib.util.find_spec
    required = ["PySide6"]
    if needs_gui:
        required.append("optiland_gui")

    missing = []
    for module in required:
        try:
            if find(module) is None:
                missing.append(module)
        except (ImportError, ValueError):
            missing.append(module)

    if not missing:
        return

    hard = [m for m in missing if m == "PySide6"]
    print(
        "\n[optiland-zh] 找不到："
        + "、".join(missing)
        + "\n\n"
        + "本包只是汉化层，**不含 Optiland 本体**。请先装上游：\n\n"
        + f"    {UPSTREAM_HINT}\n\n"
        + "（汉化包刻意不声明 optiland 依赖，免得和你已装好的 Qt 版本打架。）\n",
        file=sys.stderr,
    )
    # 缺 PySide6 时 Qt 一律用不了；缺 optiland_gui 只是启动器跑不起来
    raise SystemExit(2 if hard else 1)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optiland-zh",
        description="Optiland GUI 简体中文汉化启动器",
        add_help=True,
    )
    parser.add_argument(
        "-l",
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"界面语言（默认 {DEFAULT_LANGUAGE}）",
    )
    parser.add_argument(
        "-c",
        "--catalog",
        help="直接指定词库 JSON 文件（调试用，优先于 --language）",
    )
    parser.add_argument(
        "--no-locale",
        action="store_true",
        help="不改动 Qt locale，只替换文字",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="列出随包分发的语言后退出",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="统计词库覆盖了多少条提取出来的界面文字，然后退出",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="离屏自检：验证补丁是否真的生效，然后退出",
    )
    parser.add_argument("--version", action="version", version=f"optiland-zh {__version__}")
    return parser


# ---------------------------------------------------------------------------
# 子命令实现
# ---------------------------------------------------------------------------


def cmd_list_languages() -> int:
    for code in available_languages():
        catalog = load_catalog(code)
        print(f"  {code:<10} {catalog.display_name:<12} {len(catalog.entries)} 条词条"
              f" + {len(catalog.patterns)} 条动态规则")
    return 0


def cmd_coverage(catalog_file: str | None, language: str) -> int:
    """算出词库对当前 optiland_gui 的覆盖率。

    这需要先跑一遍提取器；找不到提取结果就现场扫一次。
    """
    import json
    from pathlib import Path

    from .extract import locate_gui_package, scan_package

    catalog = load_catalog(Path(catalog_file) if catalog_file else language)

    report = scan_package(locate_gui_package())
    static_total = len(report.static)
    static_hit = sum(1 for text in report.static if catalog.has(text))
    dynamic_total = len(report.dynamic)
    dynamic_hit = sum(1 for pattern in report.dynamic if catalog.has(pattern))

    def pct(hit: int, total: int) -> str:
        return f"{hit / total * 100:5.1f}%" if total else "  n/a"

    print(f"词库: {catalog.display_name} ({catalog.language})")
    print(f"  静态界面文字 : {static_hit:>4} / {static_total:<4} {pct(static_hit, static_total)}")
    print(f"  动态消息模板 : {dynamic_hit:>4} / {dynamic_total:<4} {pct(dynamic_hit, dynamic_total)}")
    total_hit, total_all = static_hit + dynamic_hit, static_total + dynamic_total
    print(f"  合计         : {total_hit:>4} / {total_all:<4} {pct(total_hit, total_all)}")

    if static_hit < static_total:
        missing = sorted(t for t in report.static if not catalog.has(t))
        print(f"\n未翻译的静态条目（前 30 条）:")
        for text in missing[:30]:
            print(f"    {text!r}")
        if len(missing) > 30:
            print(f"    ... 还有 {len(missing) - 30} 条")
    return 0


def cmd_self_test(language: str, catalog_file: str | None) -> int:
    """离屏验证：补丁真的把文字换掉了吗？"""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QMainWindow,
        QPushButton,
    )

    from . import install, uninstall

    app = QApplication.instance() or QApplication([])

    install(language, load_catalog(catalog_file) if catalog_file else None)

    failures: list[str] = []

    def check(label: str, got: str, expect_changed: bool = True) -> None:
        changed = got not in ("", label)
        ok = changed if expect_changed else not changed
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {label!r} -> {got!r}")
        if not ok:
            failures.append(label)

    # ① 构造器
    check("Lens Data Editor", QLabel("Lens Data Editor").text())
    # ② setText
    button = QPushButton()
    button.setText("Run Analysis")
    check("Run Analysis", button.text())
    # ③ 窗口标题
    window = QMainWindow()
    window.setWindowTitle("Optiland GUI")
    check("Optiland GUI", window.windowTitle())
    # ④ 菜单
    menu = window.menuBar().addMenu("&File")
    check("&File", menu.title())
    # ⑤ 下拉框：显示中文
    combo = QComboBox()
    combo.addItem("Spot Diagram")
    combo.addItem("Ray Fan")
    check("Spot Diagram", combo.itemText(0))
    # ⑥ ...但程序内部读到的必须还是英文（否则分析功能会失效）
    combo.setCurrentIndex(0)
    english = combo.currentText()
    ok = english == "Spot Diagram"
    print(f"  [{'OK  ' if ok else 'FAIL'}] 回译 currentText() -> {english!r} (应为 'Spot Diagram')")
    if not ok:
        failures.append("currentText 回译")

    # ⑦ 按中文文字查找，也要能找到
    index = combo.findText("Spot Diagram")
    ok = index == 0
    print(f"  [{'OK  ' if ok else 'FAIL'}] findText('Spot Diagram') -> {index} (应为 0)")
    if not ok:
        failures.append("findText")

    uninstall()

    print()
    if failures:
        print(f"自检失败 {len(failures)} 项: {', '.join(failures)}")
        return 1
    print("自检全部通过。")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.list_languages:
        # 这一条只读本包自带的词库，不需要 Qt、也不需要 Optiland
        return cmd_list_languages()

    if args.coverage:
        # 要扫 optiland_gui 的源码，必须有上游
        _require_optiland(needs_gui=True)
        return cmd_coverage(args.catalog, args.language)
    if args.self_test:
        # 自检只建控件、不碰 optiland 本体，有 PySide6 就够
        _require_optiland(needs_gui=False)
        return cmd_self_test(args.language, args.catalog)

    _require_optiland(needs_gui=True)

    from . import install

    catalog = install(
        args.language,
        load_catalog(args.catalog) if args.catalog else None,
        set_locale=not args.no_locale,
    )
    print(f"[optiland-zh] 界面语言: {catalog.display_name} "
          f"({len(catalog.entries)} 条词条, {len(catalog.patterns)} 条动态规则)")

    # 把我们已经消费掉的参数从 sys.argv 里摘干净，
    # 免得 Qt 把 --language 之类当成自己的参数。
    sys.argv = [sys.argv[0]]

    from optiland_gui.run_gui import main as gui_main

    gui_main()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
