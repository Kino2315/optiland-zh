"""打包相关的回归测试。

这些不测功能，测的是**发出去的包是不是完好的**。

为什么单独拎出来：这类问题在开发环境里全都发现不了——
源码目录还在，词库当然能读到；版本号写错也只有发布那一刻才暴露。
而发现有问题的代价是"已发布的版本不能重传，只能升版本号重发"。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    tomllib = pytest.importorskip("tomli", reason="Python 3.10 需要 tomli")

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
INIT = ROOT / "src" / "optiland_zh" / "__init__.py"
CATALOGS = ROOT / "src" / "optiland_zh" / "catalogs"


@pytest.fixture(scope="module")
def project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


class TestVersionConsistency:
    """版本号写了三处（pyproject / __init__ / 每个词库文件），漂移了要当场发现。"""

    def test_dunder_version_matches_pyproject(self, project) -> None:
        declared = project["project"]["version"]
        source = INIT.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', source)
        assert match, "src/optiland_zh/__init__.py 里找不到 __version__"
        assert match.group(1) == declared, (
            f"pyproject.toml 是 {declared}，__init__.py 是 {match.group(1)}。"
            "发布时这两个对不上会推出一个版本号错误的包。"
        )

    def test_version_is_pep440(self, project) -> None:
        version = project["project"]["version"]
        assert re.fullmatch(r"\d+\.\d+\.\d+([.-]?(a|b|rc|dev)\d+)?", version), (
            f"{version!r} 不是合法的 PEP 440 版本号"
        )

    def test_catalog_version_matches_package(self, project) -> None:
        """词库里的 version 必须和包版本一致。

        这个字段本身没人读，所以很容易在发版时被忘掉 —— 于是它会一直停在
        某个旧版本号上，变成一个**看起来有信息、实际不可信**的装饰字段。
        要么让它同步，要么删掉它；这里选前者，并用测试保证它不会漂。
        """
        import json

        declared = project["project"]["version"]
        for path in sorted(CATALOGS.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data.get("version") == declared, (
                f"{path.name} 里写的是 {data.get('version')!r}，"
                f"但包版本是 {declared!r}。发版时记得一起改。"
            )


class TestDistributionMetadata:
    def test_catalog_shipped_as_package_data(self, project) -> None:
        """词库必须声明成 package-data。

        漏了它的后果是"装完没中文"，而且开发机上完全复现不了。
        """
        data = project["tool"]["setuptools"]["package-data"]
        patterns = data["optiland_zh"]
        assert any("catalogs" in p for p in patterns), patterns

    def test_catalog_files_exist(self) -> None:
        found = sorted(p.name for p in CATALOGS.glob("*.json"))
        assert found, f"{CATALOGS} 下没有任何词库"
        assert "zh_CN.json" in found, f"内置语言缺了 zh_CN: {found}"

    def test_console_script_declared(self, project) -> None:
        scripts = project["project"]["scripts"]
        assert scripts.get("optiland-zh") == "optiland_zh.launcher:main"

    def test_license_uses_spdx_not_classifier(self, project) -> None:
        """PEP 639：用了 SPDX 表达式就不能再写 License 分类器。

        两者同时存在时 setuptools >= 77 会直接报错，构建都过不去。
        """
        assert project["project"]["license"] == "MIT"
        classifiers = project["project"].get("classifiers", [])
        offenders = [c for c in classifiers if c.startswith("License ::")]
        assert not offenders, (
            f"已经用了 license = \"MIT\"，就不能再有这些分类器: {offenders}"
        )

    def test_license_file_declared(self, project) -> None:
        assert "LICENSE" in project["project"]["license-files"]

    def test_readme_has_explicit_content_type(self, project) -> None:
        """不写 content-type 就得让 PyPI 猜，猜错整个项目页是一堆原始 Markdown。"""
        readme = project["project"]["readme"]
        assert isinstance(readme, dict), "readme 应该写成 { file = ..., content-type = ... }"
        assert readme["content-type"] == "text/markdown"

    def test_requires_python_matches_classifiers(self, project) -> None:
        """requires-python 的下界要和 Python 版本分类器对得上。

        写 ">=3.10" 却只列 3.11+ 的分类器，会让 3.10 用户以为不支持。
        """
        floor = re.search(r">=(\d+)\.(\d+)", project["project"]["requires-python"])
        assert floor, project["project"]["requires-python"]
        minor = int(floor.group(2))
        classifiers = project["project"].get("classifiers", [])
        declared = [
            int(m.group(1))
            for c in classifiers
            if (m := re.search(r"Programming Language :: Python :: 3\.(\d+)$", c))
        ]
        assert declared, "一个 Python 版本分类器都没写"
        assert min(declared) == minor, (
            f"requires-python 下界是 3.{minor}，分类器最小却是 3.{min(declared)}"
        )


class TestReadmeLinks:
    """README 会原样渲染到 PyPI 上，相对链接在那儿全是断的。"""

    def test_no_relative_image_links(self) -> None:
        for name in ("README.md", "README.en.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            bad = [
                m.group(1)
                for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text)
                if not m.group(1).startswith("http")
            ]
            assert not bad, (
                f"{name} 里有相对图片链接 {bad}；PyPI 上会显示成破图，"
                "要用 raw.githubusercontent.com 的绝对地址"
            )

    def test_no_relative_doc_links(self) -> None:
        for name in ("README.md", "README.en.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            bad = [
                m.group(1)
                for m in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", text)
                if not m.group(1).startswith(("http", "#"))
            ]
            assert not bad, (
                f"{name} 里有相对文档链接 {bad}；PyPI 上会 404，"
                "要用 github.com 的绝对地址"
            )
