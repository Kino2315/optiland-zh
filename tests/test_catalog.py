"""词库的单元测试 —— 纯数据，不需要 Qt。

这个文件刻意保持**零 Qt 依赖**：CI 里有一个不装 PySide6 的快速任务只跑它。
引擎那部分（需要 Qt）搬到了 test_engine.py。

为什么非要分开：模块级的 pytest.importorskip 命不中时会跳过**整个文件**，
于是那个「不装 Qt」的任务会全绿通过、却一条断言都没跑 —— 比红更糟。

    pytest -q
"""

from __future__ import annotations

import json

import pytest

# --- 纯逻辑：不需要 Qt ------------------------------------------------------

from optiland_zh.catalog import (
    Catalog,
    CatalogError,
    available_languages,
    compile_pattern,
    load_catalog,
)


class TestCatalog:
    def setup_method(self) -> None:
        self.catalog = load_catalog("zh_CN")

    def test_builtin_language_exists(self) -> None:
        assert "zh_CN" in available_languages()

    def test_static_lookup(self) -> None:
        assert self.catalog.translate("Lens Data Editor") == "镜头数据编辑器"

    def test_unknown_text_passes_through(self) -> None:
        # 没翻译过的文字必须原样返回，否则界面会出现空白
        assert self.catalog.translate("zzz not a real string") == "zzz not a real string"

    def test_empty_string(self) -> None:
        assert self.catalog.translate("") == ""

    def test_whitespace_tolerant_lookup_keeps_indentation(self) -> None:
        """优化器下拉项用前导空格做对齐，词库不该为每种缩进写一份。"""
        assert self.catalog.translate("Least Squares") == "最小二乘"
        assert self.catalog.translate("  Least Squares") == "  最小二乘"
        assert self.catalog.translate("Least Squares  ") == "最小二乘  "

    def test_dynamic_pattern(self) -> None:
        got = self.catalog.translate("Field 2: (0.000, 1.000)")
        assert got == "视场 2：(0.000, 1.000)"

    def test_pattern_captures_are_retranslated(self) -> None:
        """捕获组里的英文也要过一遍词条。

        否则 "Toggle Analysis" 会变成「显示/隐藏 Analysis」这种半中半英。
        """
        assert self.catalog.translate("Toggle Analysis") == "显示/隐藏 分析"

    def test_multiline_pattern(self) -> None:
        """动态正则必须用 DOTALL，否则跨行的消息匹配不上。"""
        got = self.catalog.translate("Could not save file:\n[Errno 13] denied")
        assert got == "无法保存文件：\n[Errno 13] denied"

    def test_has_covers_entries_and_patterns(self) -> None:
        assert self.catalog.has("Lens Data Editor")
        assert self.catalog.has("Field {0}: ({1}, {2})")
        assert not self.catalog.has("nope")

    def test_duplicate_translations_is_a_report_not_an_error(self) -> None:
        c = Catalog.from_dict(
            {"entries": {"A": "相同", "B": "相同", "C": "不同"}}
        )
        dupes = c.duplicate_translations()
        assert "相同" in dupes
        assert set(dupes["相同"]) == {"A", "B"}

    def test_bad_json_reports_clearly(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        with pytest.raises(CatalogError, match="不是合法 JSON"):
            Catalog.load(bad)

    def test_pattern_must_have_both_fields(self) -> None:
        with pytest.raises(CatalogError, match="match 和 replace"):
            Catalog.from_dict({"patterns": [{"match": "x"}]})

    def test_missing_language_lists_alternatives(self) -> None:
        with pytest.raises(CatalogError, match="可用的有"):
            load_catalog("xx_XX")


class TestPatternCompiler:
    def test_repeated_placeholder(self) -> None:
        """同一占位符出现两次也要能编译（命名组不能重名）。"""
        p = compile_pattern("{0} and {0}", "「{0}」和「{0}」")
        assert p.apply("a and a") == "「a」和「a」"

    def test_placeholders_can_be_reordered(self) -> None:
        p = compile_pattern("({0}, {1})", "（先 {1} 后 {0}）")
        assert p.apply("(x, y)") == "（先 y 后 x）"

    def test_no_placeholder_is_an_exact_match(self) -> None:
        p = compile_pattern("hello", "你好")
        assert p.apply("hello") == "你好"
        assert p.apply("hello!") is None

    def test_regex_metacharacters_are_escaped(self) -> None:
        """模板里的 ( ) . 必须当字面量，不能当正则元字符。"""
        p = compile_pattern("Field (0)", "视场 (0)")
        assert p.apply("Field (0)") == "视场 (0)"
        assert p.apply("Field 0") is None


class TestCatalogIntegrity:
    """对内置词库做体检，防止手改 JSON 时改坏。"""

    def setup_method(self) -> None:
        self.catalog = load_catalog("zh_CN")
        # 重新读原始 JSON，检查结构而不是编译结果
        from pathlib import Path

        path = Path(__file__).parent.parent / "src" / "optiland_zh" / "catalogs" / "zh_CN.json"
        self.raw = json.loads(path.read_text(encoding="utf-8"))

    def test_every_entry_has_a_translation(self) -> None:
        empty = [k for k, v in self.raw["entries"].items() if not v.strip()]
        assert not empty, f"这些词条译文是空的: {empty}"

    def test_printf_placeholders_preserved(self) -> None:
        """%s / %d 的数量必须一致，否则运行期格式化会炸。"""
        import re

        for english, chinese in self.catalog.entries.items():
            src = re.findall(r"%[sd]", english)
            dst = re.findall(r"%[sd]", chinese)
            assert src == dst, f"{english!r} -> {chinese!r} 占位符对不上"

    def test_mnemonic_kept(self) -> None:
        """带 & 快捷键的菜单项，译文也要有 &。"""
        for english, chinese in self.catalog.entries.items():
            if english.startswith("&") and len(english) > 2:
                assert "&" in chinese, f"{english!r} -> {chinese!r} 丢了快捷键"

    def test_html_tags_preserved(self) -> None:
        for english, chinese in self.catalog.entries.items():
            import re

            tags = re.findall(r"</?[a-z0-9]+>", english)
            for tag in tags:
                assert tag in chinese, f"{english!r} -> {chinese!r} 丢了 {tag}"

    def test_file_dialog_filters_keep_globs(self) -> None:
        for english, chinese in self.catalog.entries.items():
            if ";;" in english:
                for part in english.split(";;"):
                    glob = part[part.find("(") :]
                    assert glob in chinese, f"{english!r} -> {chinese!r} 丢了 {glob}"

    def test_font_name_not_translated(self) -> None:
        """字体名翻了会换字体。"""
        assert "Cascadia Code" not in self.catalog.entries

    def test_pattern_match_templates_are_not_modified(self) -> None:
        """patterns 的 match 是匹配键，必须保持英文原样。"""
        for p in self.raw["patterns"]:
            assert not any("\u4e00" <= ch <= "\u9fff" for ch in p["match"]), (
                f"match 里混进了中文: {p['match']!r}"
            )
