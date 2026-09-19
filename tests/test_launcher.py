"""启动器的行为测试 —— 不需要 Qt。

这里测的不是"能不能启动 GUI"，而是**装错东西时有没有说人话**。

背景：本项目刻意不声明 ``optiland`` 依赖（免得和用户已装好的 Qt 版本打架），
代价是用户很容易只装汉化包就跑，然后撞上::

    ModuleNotFoundError: No module named 'PySide6'

这个报错完全指不出下一步该干什么。所以启动前先自己检查一遍，
换成一句能照着做的提示 —— 而这些测试就是保证那句话还在。
"""

from __future__ import annotations

import pytest

from optiland_zh.launcher import UPSTREAM_HINT, _require_optiland, build_parser, cmd_list_languages


def _finder(present: set[str]):
    """造一个假的 importlib.util.find_spec。"""

    def find(name: str):
        return object() if name in present else None

    return find


class TestRequireOptiland:
    def test_raises_when_pyside6_missing(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _require_optiland(needs_gui=True, finder=_finder(set()))

        # 缺 Qt 是硬失败
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert UPSTREAM_HINT in err, "提示里必须给出可照抄的安装命令"
        assert "不含 Optiland 本体" in err, "要说清本包只是汉化层"

    def test_raises_when_only_optiland_gui_missing(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _require_optiland(needs_gui=True, finder=_finder({"PySide6"}))

        assert exc.value.code == 1
        assert "optiland_gui" in capsys.readouterr().err

    def test_passes_when_everything_present(self) -> None:
        _require_optiland(
            needs_gui=True, finder=_finder({"PySide6", "optiland_gui"})
        )

    def test_self_test_only_needs_qt(self) -> None:
        """--self-test 只建控件，不碰 optiland 本体，所以不该要求它。"""
        _require_optiland(needs_gui=False, finder=_finder({"PySide6"}))

    def test_self_test_still_needs_qt(self, capsys) -> None:
        with pytest.raises(SystemExit):
            _require_optiland(needs_gui=False, finder=_finder(set()))
        assert UPSTREAM_HINT in capsys.readouterr().err

    def test_broken_finder_is_treated_as_missing(self, capsys) -> None:
        """某些环境下 find_spec 会因为父包报错，不能让它冒出去。"""

        def boom(name: str):
            raise ImportError("parent package is not a package")

        with pytest.raises(SystemExit):
            _require_optiland(needs_gui=True, finder=boom)
        assert UPSTREAM_HINT in capsys.readouterr().err


class TestArgumentParsing:
    def test_help_works_without_qt(self) -> None:
        """argparse 阶段绝不能碰 Qt，否则 --help 都用不了。"""
        parser = build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--help"])
        assert exc.value.code == 0

    def test_default_language(self) -> None:
        args = build_parser().parse_args([])
        assert args.language == "zh_CN"
        assert not args.no_locale

    def test_flag_parsing(self) -> None:
        args = build_parser().parse_args(
            ["-l", "zh_TW", "-c", "x.json", "--no-locale", "--coverage"]
        )
        assert args.language == "zh_TW"
        assert args.catalog == "x.json"
        assert args.no_locale
        assert args.coverage


class TestListLanguages:
    def test_works_without_qt(self, capsys) -> None:
        """--list-languages 只读本包自带的词库，任何环境都该能用。"""
        assert cmd_list_languages() == 0
        out = capsys.readouterr().out
        assert "zh_CN" in out
        assert "简体中文" in out
