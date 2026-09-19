"""快捷方式创建的测试。

这里能测的部分都是"纯逻辑"：路径解析、`.desktop` 的内容、清理行为。
真正创建 Windows `.lnk` 要调 PowerShell，那部分由 CI 的
windows-latest 矩阵跑（Linux 上则走 `.desktop` 那条分支）。

不测的部分也要说清楚：**测不到"双击之后真的没有黑框"**。
那个靠的是 PE 头的 Subsystem 字段（2=GUI / 3=CUI），由
`pyproject.toml` 的 `[project.gui-scripts]` 决定，不是运行时行为。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from optiland_zh import shortcut


class TestDesktopDir:
    def test_returns_a_path(self) -> None:
        d = shortcut.desktop_dir()
        # Windows 走 SHGetFolderPathW，其余平台退回 ~/Desktop 或 ~/桌面。
        # 极端环境下可能拿不到，那时应当返回 None 而不是抛异常。
        assert d is None or isinstance(d, Path)

    def test_does_not_hardcode_english_desktop(self) -> None:
        """中文 Windows 上桌面目录叫「桌面」，不能只认 ~/Desktop。"""
        source = Path(shortcut.__file__).read_text(encoding="utf-8")
        assert "桌面" in source, "应当同时尝试「桌面」这个名字"


class TestLauncherPath:
    def test_console_and_gui_are_different_names(self) -> None:
        assert shortcut.CONSOLE_SCRIPT != shortcut.GUI_SCRIPT

    def test_resolves_when_installed(self) -> None:
        """包正常安装时应该能找到入口脚本。"""
        found = shortcut.launcher_path(gui=True)
        if found is None:
            pytest.skip("当前环境没装入口脚本（比如直接从源码跑 pytest）")
        assert found.exists()
        assert shortcut.GUI_SCRIPT in found.name


class TestDesktopEntry:
    def test_has_required_keys(self) -> None:
        text = shortcut._desktop_entry(Path("/opt/bin/optiland-zh-gui"), None)
        for key in ("[Desktop Entry]", "Type=Application", "Name=", "Exec=", "Terminal="):
            assert key in text, f".desktop 缺 {key}"

    def test_terminal_is_false(self) -> None:
        """Terminal=true 会弹出控制台，那正是我们要避免的。"""
        text = shortcut._desktop_entry(Path("/x"), None)
        assert "Terminal=false" in text

    def test_icon_line_only_when_given(self) -> None:
        assert "Icon=" not in shortcut._desktop_entry(Path("/x"), None)
        assert "Icon=/tmp/i.ico" in shortcut._desktop_entry(Path("/x"), Path("/tmp/i.ico"))

    def test_ends_with_newline(self) -> None:
        assert shortcut._desktop_entry(Path("/x"), None).endswith("\n")


class TestUninstall:
    def test_empty_dir_returns_nothing(self, tmp_path: Path) -> None:
        assert shortcut.uninstall(desktop=tmp_path) == []

    def test_removes_both_known_names(self, tmp_path: Path) -> None:
        for name in (f"{shortcut.SHORTCUT_NAME}.lnk", f"{shortcut.SHORTCUT_NAME}.desktop"):
            (tmp_path / name).write_text("x", encoding="utf-8")
        removed = shortcut.uninstall(desktop=tmp_path)
        assert len(removed) == 2
        assert not any(tmp_path.iterdir())

    def test_leaves_other_shortcuts_alone(self, tmp_path: Path) -> None:
        """只删自己建的名字，不动用户手工做的快捷方式。"""
        mine = tmp_path / f"{shortcut.SHORTCUT_NAME}.lnk"
        theirs = tmp_path / "我的 Chrome.lnk"
        mine.write_text("x", encoding="utf-8")
        theirs.write_text("x", encoding="utf-8")

        shortcut.uninstall(desktop=tmp_path)

        assert not mine.exists()
        assert theirs.exists(), "不该动用户自己做的快捷方式"


class TestInstallGuards:
    def test_missing_desktop_dir_raises(self, tmp_path: Path) -> None:
        if shortcut.launcher_path(gui=True) is None:
            pytest.skip("没有入口脚本，测不到这个分支")
        missing = tmp_path / "does-not-exist"
        with pytest.raises(RuntimeError, match="桌面目录"):
            shortcut.install(desktop=missing)

    @pytest.mark.skipif(
        sys.platform == "darwin",
        reason="macOS 分支就是设计成报错的，另有测试覆盖",
    )
    def test_creates_a_file_on_supported_platforms(self, tmp_path: Path) -> None:
        if shortcut.launcher_path(gui=True) is None:
            pytest.skip("没有入口脚本")
        link = shortcut.install(desktop=tmp_path)
        assert link.exists()
        assert link.parent == tmp_path
        if sys.platform == "win32":
            assert link.suffix == ".lnk"
        elif sys.platform.startswith("linux"):
            assert link.suffix == ".desktop"
            # GNOME 会把没有执行位的 .desktop 当成文本文件
            assert link.stat().st_mode & 0o111
