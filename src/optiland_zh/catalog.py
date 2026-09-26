"""词库：加载、匹配、翻译。

词库是纯数据（JSON），放在 ``catalogs/`` 下，一种语言一个文件。
这样社区加词条、加语言都不用碰 Python 代码。

格式
----
::

    {
      "language": "zh_CN",
      "display_name": "简体中文",
      "entries": {
        "&File": "文件(&F)",
        "Lens Data Editor": "镜头数据编辑器"
      },
      "patterns": [
        {
          "match":   "Field {0}: ({1}, {2})",
          "replace": "视场 {0}：({1}, {2})",
          "comment": "视场表格里的一行"
        }
      ]
    }

``patterns`` 用 ``{0} {1} ...`` 占位，运行期编译成正则。
比让翻译者写 ``(?P<n>.+?)`` 友好得多，也不容易写错。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Callable

DEFAULT_LANGUAGE = "zh_CN"

# 模板里的占位符：{0} {1} ... 或 {name}
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*|\d+)\}")


class CatalogError(RuntimeError):
    """词库文件有问题。"""


@dataclass
class _CompiledPattern:
    """一条编译好的动态规则。"""

    regex: re.Pattern[str]
    # 正则里的组名 -> 模板里的占位符名。用 g0/g1 是为了允许同一占位符重复出现
    group_to_placeholder: list[str]
    replace_template: str
    source: str

    def apply(self, text: str, exact_lookup: Callable[[str], str | None] | None = None) -> str | None:
        """匹配并回填。

        ``exact_lookup`` 会把**捕获到的内容**再过一遍静态词条。这一步很关键：
        ``"Toggle {0}"`` 命中时 ``{0}`` 是 ``"Analysis"``，如果不查一下就回填，
        结果是「显示/隐藏 Analysis」这种半中半英；查过之后才是「显示/隐藏 分析」。
        """
        match = self.regex.match(text)
        if match is None:
            return None
        values: dict[str, str] = {}
        for index, placeholder in enumerate(self.group_to_placeholder):
            captured = match.group(f"g{index}")
            if exact_lookup is not None:
                translated = exact_lookup(captured)
                if translated is not None:
                    captured = translated
            values[placeholder] = captured
        return _PLACEHOLDER.sub(
            lambda m: values.get(m.group(1), m.group(0)), self.replace_template
        )


def compile_pattern(match_template: str, replace_template: str) -> _CompiledPattern:
    """把 ``"Field {0}: ({1}, {2})"`` 编译成正则 + 回填模板。"""
    parts: list[str] = []
    placeholders: list[str] = []
    cursor = 0
    for hit in _PLACEHOLDER.finditer(match_template):
        parts.append(re.escape(match_template[cursor : hit.start()]))
        parts.append(f"(?P<g{len(placeholders)}>.+?)")
        placeholders.append(hit.group(1))
        cursor = hit.end()
    parts.append(re.escape(match_template[cursor:]))
    regex = re.compile("^" + "".join(parts) + "$", re.DOTALL)
    return _CompiledPattern(regex, placeholders, replace_template, match_template)


def normalize_for_lookup(text: str) -> str:
    """把界面上的文字归一化，用来和词库里的键比对。

    Qt 渲染同一句话时，会按控件类型把**快捷键标记 ``&``** 和**结尾的省略号**
    去掉，所以「屏幕上看到的」和「词库里的键」经常差一两个字符：

        词库里的键      &Save System
        菜单里看到的    &Save System
        工具栏上看到的   Save System

    查词时两边都过一遍这个函数，就不会因为差一个 ``&`` 而查不到。
    同一个东西出现两种形态，实测在界面里很常见（`保存系统(&S)` 和 `保存系统(S)`
    同时存在）。
    """
    text = text.replace("&", "")
    text = re.sub(r"(\.\.\.|…)+$", "", text)
    return text.strip()


def _matches_template(text: str, template: str) -> bool:
    """``text`` 是不是 ``template`` 拼出来的？

    把模板当成 ``match`` 模板重新编译一遍就能反过来匹配它 ——
    「显示/隐藏 {0}」编译成正则之后，能匹配「显示/隐藏 分析」。
    """
    try:
        return compile_pattern(template, template).regex.match(text) is not None
    except re.error:
        return False


@dataclass
class Catalog:
    """一种语言的词库。"""

    language: str
    display_name: str
    entries: dict[str, str] = field(default_factory=dict)
    patterns: list[_CompiledPattern] = field(default_factory=list)
    source_path: Path | None = None
    # 翻译缓存：界面文字会被反复设置（比如表格逐格刷新），缓存能省掉大量正则尝试
    _cache: dict[str, str] = field(default_factory=dict, repr=False)

    # -- 构造 --------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict, source_path: Path | None = None) -> "Catalog":
        if not isinstance(data, dict):
            raise CatalogError("词库根节点必须是 JSON 对象")
        language = data.get("language") or DEFAULT_LANGUAGE
        entries = data.get("entries") or {}
        if not isinstance(entries, dict):
            raise CatalogError(f"{language}: entries 必须是对象")

        patterns: list[_CompiledPattern] = []
        for index, item in enumerate(data.get("patterns") or []):
            if not isinstance(item, dict) or "match" not in item or "replace" not in item:
                raise CatalogError(
                    f"{language}: patterns[{index}] 必须同时有 match 和 replace"
                )
            patterns.append(compile_pattern(item["match"], item["replace"]))

        return cls(
            language=language,
            display_name=data.get("display_name") or language,
            entries=dict(entries),
            patterns=patterns,
            source_path=source_path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "Catalog":
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CatalogError(f"找不到词库: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CatalogError(f"词库不是合法 JSON: {path}: {exc}") from exc
        return cls.from_dict(data, source_path=path)

    # -- 查询 --------------------------------------------------------------

    def translate(self, text: str) -> str:
        """把英文界面文字换成译文；命不中就原样返回。"""
        if not text:
            return text
        cached = self._cache.get(text)
        if cached is not None:
            return cached

        result = self.entries.get(text)
        if result is None and text != text.strip():
            # 容忍首尾空白：优化器的下拉项带前导空格做视觉对齐
            # （如 " Least Squares"），词库键不会为每种缩进各写一份。
            # 回填时把原来的缩进还回去，免得破坏对齐。
            stripped_hit = self.entries.get(text.strip())
            if stripped_hit is not None:
                lead = text[: len(text) - len(text.lstrip())]
                trail = text[len(text.rstrip()) :]
                result = f"{lead}{stripped_hit}{trail}"
        if result is None:
            # 动态串只在含空格时才有可能是模板，先做个廉价过滤
            if " " in text or "\n" in text:
                for pattern in self.patterns:
                    hit = pattern.apply(text, self.entries.get)
                    if hit is not None:
                        result = hit
                        break
        if result is None:
            result = text

        # 缓存不要无限增长：界面字符串总量有限，但动态串可能带文件名之类，
        # 超过阈值就整体清空，简单且不会内存泄漏。
        if len(self._cache) > 4096:
            self._cache.clear()
        self._cache[text] = result
        return result

    def has(self, text: str) -> bool:
        """这条字符串有没有被覆盖（静态词条或动态规则都算）。

        给覆盖率统计用：``entries`` 管静态文字，``patterns`` 管动态模板，
        漏掉后者会把动态覆盖率永远算成 0%。
        """
        if text in self.entries:
            return True
        return any(p.source == text for p in self.patterns)

    def coverage_of(self, static: list[str], dynamic: list[str]) -> tuple[int, int]:
        """一次算出 (已覆盖, 总数)。"""
        hit = sum(1 for t in static if t in self.entries)
        hit += sum(1 for t in dynamic if any(p.source == t for p in self.patterns))
        return hit, len(static) + len(dynamic)

    def lookup(self, text: str) -> dict[str, str] | None:
        """查一句界面文字和词库的关系。查不到返回 ``None``。

        给 ``optiland-zh --lookup`` 用：你在界面上看到一句话，想知道它为什么没翻。

        返回的 dict 里 ``how`` 说明是怎么对上的：

        ==============  ==============================================
        ``exact``       文字和词库里的键逐字符相等
        ``normalized``  去掉 ``&`` 和结尾省略号之后相等
        ``value``       你给的是**译文**，不是英文原文
        ``pattern``     命中了某条动态规则（见下面的 ``side``）
        ==============  ==============================================

        ``how == "pattern"`` 时另带 ``side``：``"en"`` 表示你给的英文原文
        会被这条规则翻掉；``"zh"`` 表示你给的中文是这条规则拼出来的。
        pattern 档都带 ``key``（英文模板）和 ``template``（中文模板）。
        """
        if text in self.entries:
            return {"how": "exact", "key": text, "value": self.entries[text]}

        normalized = normalize_for_lookup(text)
        if normalized:
            for key, value in self.entries.items():
                if normalize_for_lookup(key) == normalized:
                    return {"how": "normalized", "key": key, "value": value}

        # 给的是译文
        for key, value in self.entries.items():
            if value == text:
                return {"how": "value", "key": key, "value": value}

        # 动态规则：两个方向都要试
        for pattern in self.patterns:
            # ① 英文原文命中规则的 match 模板 —— 「Toggle Analysis」来自「Toggle {0}」
            if pattern.regex.match(text) is not None:
                return {
                    "how": "pattern",
                    "side": "en",
                    "key": pattern.source,
                    "template": pattern.replace_template,
                }
            # ② 中文是规则的 replace 模板拼出来的 —— 「显示/隐藏 分析」来自「显示/隐藏 {0}」
            if pattern.replace_template == text or _matches_template(
                text, pattern.replace_template
            ):
                return {
                    "how": "pattern",
                    "side": "zh",
                    "key": pattern.source,
                    "template": pattern.replace_template,
                }

        return None

    # -- 诊断 --------------------------------------------------------------

    def duplicate_translations(self) -> dict[str, list[str]]:
        """找出"多个英文对应同一句中文"的情况。

        这类冲突本身不致命——运行时靠控件自带的原文（userData）回译，
        不依赖反向查表。但如果有人想拿词库做反向翻译，这就是歧义点，
        所以单独报出来供译者检查。
        """
        reverse: dict[str, list[str]] = {}
        for english, chinese in self.entries.items():
            reverse.setdefault(chinese, []).append(english)
        return {zh: ens for zh, ens in reverse.items() if len(ens) > 1}


def catalog_path(language: str = DEFAULT_LANGUAGE) -> Path:
    """内置词库的文件路径。"""
    return Path(str(resources.files("optiland_zh").joinpath("catalogs", f"{language}.json")))


def available_languages() -> list[str]:
    """列出随包分发的所有语言。"""
    root = resources.files("optiland_zh").joinpath("catalogs")
    return sorted(
        item.name[: -len(".json")]
        for item in root.iterdir()
        if item.name.endswith(".json")
    )


def load_catalog(language: str | Path = DEFAULT_LANGUAGE) -> Catalog:
    """载入词库。

    ``language`` 可以是语言代码（``"zh_CN"``，读内置词库），
    也可以是一个文件路径（读自定义词库，方便本地调试和社区分支）。
    """
    if isinstance(language, Path) or (
        isinstance(language, str) and language.endswith(".json")
    ):
        return Catalog.load(language)
    path = catalog_path(language)
    if not path.exists():
        raise CatalogError(
            f"没有内置语言 '{language}'。可用的有: {', '.join(available_languages())}"
        )
    return Catalog.load(path)
