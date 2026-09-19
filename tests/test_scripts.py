"""测试 ``scripts/`` 下的 CI 辅助脚本。

为什么这些脚本也要有测试
------------------------
``check_description.py`` 存在的理由是"``twine check`` 对 Markdown 其实
什么都没验证"。如果它自己又悄悄不检查了，就会变成同一类问题的第二份 ——
一个永远绿、什么都不干的关卡，比没有关卡更糟，因为它会让人以为有保障。

所以这里直接测它的判定函数，正例反例都覆盖。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_description.py"


@pytest.fixture(scope="module")
def checker():
    """把脚本当模块加载。

    ``scripts/`` 不是包（没有 ``__init__.py``），也不该为了测试它
    而变成一个包，所以用 importlib 按路径加载。
    """
    assert SCRIPT.exists(), f"检查脚本不见了: {SCRIPT}"
    spec = importlib.util.spec_from_file_location("check_description", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestProblemsIn:
    def test_all_absolute_passes(self, checker) -> None:
        html = '<img src="https://a/b.png"><a href="https://x/y">z</a>'
        assert checker.problems_in(html) == []

    def test_relative_image_is_flagged(self, checker) -> None:
        problems = checker.problems_in('<img src="docs/shot.png">')
        assert len(problems) == 1
        assert "docs/shot.png" in problems[0]
        assert "破图" in problems[0]

    def test_relative_link_is_flagged(self, checker) -> None:
        problems = checker.problems_in('<a href="CONTRIBUTING.md">c</a>')
        assert len(problems) == 1
        assert "CONTRIBUTING.md" in problems[0]
        assert "404" in problems[0]

    def test_anchor_allowed(self, checker) -> None:
        assert checker.problems_in('<a href="#install">i</a>') == []

    def test_mailto_allowed(self, checker) -> None:
        assert checker.problems_in('<a href="mailto:a@b.c">m</a>') == []

    def test_data_uri_allowed(self, checker) -> None:
        assert checker.problems_in('<img src="data:image/png;base64,AAA">') == []

    def test_reports_both_kinds_together(self, checker) -> None:
        problems = checker.problems_in('<img src="a.png"><a href="b.md">x</a>')
        assert len(problems) == 2

    def test_empty_html_is_fine(self, checker) -> None:
        assert checker.problems_in("") == []


class TestScriptContract:
    def test_die_exits_nonzero_with_message(self, checker, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            checker.die("boom")
        assert exc.value.code == 1
        assert "boom" in capsys.readouterr().err

    def test_missing_backend_is_reported_as_such(self, checker) -> None:
        """后端缺失时 render() 返回 None，长得和"README 坏了"一模一样。

        这个脚本必须先分辨清楚，否则会把人引向错误的排查方向 ——
        我自己就踩过这一下。
        """
        source = SCRIPT.read_text(encoding="utf-8")
        assert "readme_renderer[md]" in source, (
            "缺少渲染后端时应该提示装 readme_renderer[md]，"
            "而不是报『渲染失败』"
        )

    def test_explains_why_twine_check_is_not_enough(self, checker) -> None:
        """脚本存在的理由要写在里面，否则后人会问"有 twine check 了还搞这个干嘛"。"""
        source = SCRIPT.read_text(encoding="utf-8")
        assert "text/markdown" in source and "twine" in source.lower()
