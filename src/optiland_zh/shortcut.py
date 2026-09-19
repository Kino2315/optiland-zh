"""为桌面创建启动快捷方式。

为什么做成一条显式命令，而不是装包时自动建
------------------------------------------
``pip install`` 不该去动用户的桌面。那样做有三个问题：侵入性强、在 CI 和
无桌面环境里会失败得莫名其妙、而且用户卸载时留下的残留没人清理。

所以这里只提供一条命令，用户想要才建：

    optiland-zh --install-shortcut

平台差异
--------
- **Windows** —— 生成 ``.lnk``。走 PowerShell 的 ``WScript.Shell``，
  不引入 pywin32 这类新依赖。
- **Linux** —— 生成 ``.desktop`` 文件，纯 Python 写文本。
- **macOS** —— 没有"桌面快捷方式"这个惯例，直接打印手工步骤。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

SHORTCUT_NAME = "Optiland 中文版"

# 双击用无控制台版本；终端用带控制台的。两个入口见 pyproject.toml。
GUI_SCRIPT = "optiland-zh-gui"
CONSOLE_SCRIPT = "optiland-zh"


def desktop_dir() -> Path | None:
    """当前用户的桌面目录。

    不硬编码 ``~/Desktop`` —— 中文 Windows 上它是「桌面」，
    而且用户可能把它重定向到别处。
    """
    if sys.platform == "win32":  # pragma: no cover - 平台分支
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0:
                return Path(buf.value)
        except Exception:
            pass
    for name in ("Desktop", "桌面"):
        candidate = Path.home() / name
        if candidate.is_dir():
            return candidate
    return None


def launcher_path(gui: bool = True) -> Path | None:
    """找到启动器可执行文件。

    优先用 PATH 上的（``shutil.which`` 会处理 .exe 后缀和跨平台差异），
    找不到就退回 ``sys.executable`` 同目录 —— venv 里 Scripts 和
    python.exe 是并排的。
    """
    name = GUI_SCRIPT if gui else CONSOLE_SCRIPT
    found = shutil.which(name)
    if found:
        return Path(found)
    beside = Path(sys.executable).parent / name
    for suffix in ("", ".exe", ".cmd", ".bat"):
        candidate = Path(str(beside) + suffix)
        if candidate.exists():
            return candidate
    return None


def ensure_icon() -> Path | None:
    """从 optiland_gui 自带的 PNG 生成 .ico，返回路径。

    ``.lnk`` 的 IconLocation 用 ``.ico`` 才可靠，PNG 在部分 Windows 版本上
    不显示。Pillow 不是本项目的声明依赖，但 matplotlib 依赖它，而装了
    ``optiland[gui]`` 就一定有 matplotlib —— 拿不到就返回 None，
    快捷方式用默认图标，不影响功能。
    """
    if sys.platform != "win32":  # pragma: no cover - 平台分支
        return None
    try:
        from PIL import Image
        import optiland_gui
    except ImportError:
        return None

    source = Path(optiland_gui.__file__).parent / "resources" / "icons" / "optiland_icon.png"
    if not source.exists():
        return None

    target_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "optiland-zh"
    target = target_dir / "optiland-zh.ico"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        image = Image.open(source).convert("RGBA")
        image.save(
            target,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    except Exception:
        return None
    return target if target.exists() else None


def _install_windows(link: Path, exe: Path, workdir: Path, icon: Path | None) -> None:
    """用 PowerShell 的 WScript.Shell 建 .lnk。

    不用 pywin32：为一个快捷方式引入一个新依赖不划算。
    注意脚本里的路径必须转义单引号（PowerShell 单引号字符串里 '' 表示一个 '）。
    """

    def ps(path: Path) -> str:
        return str(path).replace("'", "''")

    icon_line = f"$s.IconLocation = '{ps(icon)},0';" if icon else ""
    script = (
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{ps(link)}');"
        f"$s.TargetPath = '{ps(exe)}';"
        f"$s.WorkingDirectory = '{ps(workdir)}';"
        f"{icon_line}"
        "$s.Description = 'Optiland 光学设计软件（简体中文界面）';"
        "$s.Save()"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        # 必须显式给编码。不给的话 subprocess 用系统 locale 解码，而在
        # 非中文的 Windows（比如 CI 的英文 runner，cp1252）上解不了中文输出，
        # 会在**读取线程**里抛 UnicodeDecodeError —— 异常不冒泡到主线程，
        # 只是让 stdout/stderr 变成空的，最后表现为一句没有任何细节的
        # "创建快捷方式失败"。errors="replace" 保证再坏也不会把线程搞崩。
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not link.exists():
        detail = (result.stderr or result.stdout or "").strip()[:400]
        raise RuntimeError(
            f"创建快捷方式失败（PowerShell 退出码 {result.returncode}）。"
            + (f"\n\n{detail}" if detail else "\n\n（PowerShell 没有输出任何信息）")
        )


def _desktop_entry(exe: Path, icon: Path | None) -> str:
    """Linux 的 .desktop 内容。

    路径一律用 ``as_posix()``：``.desktop`` 里不该出现反斜杠。
    这个函数本来只在 Linux 上被调用，但写成与平台无关之后，
    测试在 Windows 上跑也能得到确定的结果。
    """
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={SHORTCUT_NAME}",
        "Name[zh_CN]=Optiland 中文版",
        "Comment=Optiland 光学设计软件（简体中文界面）",
        f"Exec={exe.as_posix()}",
        "Terminal=false",
        "Categories=Graphics;Science;Engineering;",
    ]
    if icon:
        lines.append(f"Icon={icon.as_posix()}")
    return "\n".join(lines) + "\n"


def install(gui: bool = True, desktop: Path | None = None) -> Path:
    """创建桌面快捷方式，返回创建出来的路径。

    :raises RuntimeError: 平台不支持，或找不到启动器。
    """
    exe = launcher_path(gui=gui)
    if exe is None:
        raise RuntimeError(
            f"找不到启动器 {GUI_SCRIPT if gui else CONSOLE_SCRIPT}。\n"
            "如果你是用 python -m optiland_zh.launcher 运行的，"
            "请先确认包已经正常安装（pip show optiland-gui-zh）。"
        )

    desktop = desktop or desktop_dir()
    if desktop is None or not desktop.is_dir():
        raise RuntimeError("找不到桌面目录。用 --shortcut-dir 手动指定。")

    # 快捷方式的起始目录用启动器所在处；GUI 本身不依赖 cwd，
    # 但这样用户从"属性"里看不会是一个莫名其妙的位置。
    workdir = exe.parent

    if sys.platform == "win32":
        link = desktop / f"{SHORTCUT_NAME}.lnk"
        _install_windows(link, exe, workdir, ensure_icon())
        return link

    if sys.platform.startswith("linux"):
        link = desktop / f"{SHORTCUT_NAME}.desktop"
        icon = ensure_icon()
        link.write_text(_desktop_entry(exe, icon), encoding="utf-8")
        link.chmod(0o755)  # 少了它，GNOME 会当成文本文件
        return link

    raise RuntimeError(
        "macOS 没有『桌面快捷方式』这个惯例。\n"
        f"可以自己做一个：打开「自动操作」，新建一个「应用程序」，"
        f"添加「运行 Shell 脚本」动作，内容填：\n    {exe}"
    )


def uninstall(desktop: Path | None = None) -> list[Path]:
    """删掉本工具创建的快捷方式，返回实际删掉的文件。"""
    desktop = desktop or desktop_dir()
    if desktop is None:
        return []
    removed = []
    for name in (f"{SHORTCUT_NAME}.lnk", f"{SHORTCUT_NAME}.desktop"):
        target = desktop / name
        if target.is_file():
            target.unlink()
            removed.append(target)
    return removed
