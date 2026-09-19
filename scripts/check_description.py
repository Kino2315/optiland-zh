"""校验打包产物里的项目描述能不能被 PyPI 正常渲染。

为什么需要这个
--------------
``twine check`` **对 Markdown 不做渲染**。twine 的 ``commands/check.py`` 里写着::

    _RENDERERS = {
        "text/markdown": None,   # Rendering cannot fail
    }

它对 ``text/markdown`` 直接把渲染器设成 ``None``，意思是"不会失败"，
然后报 PASSED。所以那个 PASSED 只验证了元数据结构和 RST 路径 ——
**对 Markdown 项目页一个字都没验证**。

而 README 会长在 PyPI 项目页最顶上。相对路径的图片会变成破图、
相对路径的链接会 404，而这两件事 twine 都不会告诉你。

这个脚本补上那一块：用 PyPI 同款渲染器真渲一遍，再检查链接是不是绝对地址。

用法
----
::

    pip install "readme_renderer[md]"
    python scripts/check_description.py            # 默认找 dist/*.whl
    python scripts/check_description.py some.whl
"""

from __future__ import annotations

import argparse
import email
import glob
import re
import sys
import zipfile
from pathlib import Path


def die(message: str) -> None:
    print(f"\n[check_description] {message}\n", file=sys.stderr)
    raise SystemExit(1)


def load_description(wheel: Path) -> tuple[str, str | None]:
    """从 wheel 的 METADATA 里取出 Description 和它的 content-type。

    这才是 PyPI 实际渲染的那份文本 —— 不是仓库里的 README.md。
    两者可能不一致（比如打包配置写错、或者 readme 指错文件）。
    """
    with zipfile.ZipFile(wheel) as z:
        metas = [n for n in z.namelist() if n.endswith(".dist-info/METADATA")]
        if not metas:
            die(f"{wheel.name} 里没有 METADATA，这不是一个正常的 wheel")
        message = email.message_from_bytes(z.read(metas[0]))

    content_type = message.get("Description-Content-Type")
    body = message.get_payload(decode=True)
    if body is None:
        die(f"{wheel.name} 的 METADATA 里没有 Description")
    return body.decode("utf-8"), content_type


ABSOLUTE_PREFIXES = ("http://", "https://", "data:")
LINK_PREFIXES = ("http://", "https://", "#", "mailto:")


def problems_in(html: str) -> list[str]:
    """返回渲染结果里的地址问题清单。

    抽成独立函数是为了能被单元测试直接调用 —— 否则这个检查脚本自己
    就会变成"永远绿但没检查东西"的东西，正是它要防的那类问题。

    PyPI 不解析相对路径：图片显示成破图、链接 404，而**渲染本身不会报错**，
    所以只能这样自己查。
    """
    images = re.findall(r'<img[^>]+src="([^"]*)"', html)
    links = re.findall(r'<a[^>]+href="([^"]*)"', html)

    problems: list[str] = []
    bad_images = [u for u in images if not u.startswith(ABSOLUTE_PREFIXES)]
    bad_links = [u for u in links if not u.startswith(LINK_PREFIXES)]

    if bad_images:
        problems.append("图片用了相对路径，PyPI 上会显示成破图：" + ", ".join(bad_images))
    if bad_links:
        problems.append("链接用了相对路径，PyPI 上会 404：" + ", ".join(bad_links))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/check_description.py",
        description="用 PyPI 同款渲染器校验 wheel 里的项目描述",
    )
    parser.add_argument(
        "wheel",
        nargs="?",
        help="要检查的 wheel；默认取 dist/*.whl",
    )
    args = parser.parse_args(argv)

    wheel = Path(args.wheel) if args.wheel else None
    if wheel is None:
        found = sorted(glob.glob("dist/*.whl"))
        if not found:
            die("dist/ 下没有 wheel。先跑：python -m build")
        wheel = Path(found[-1])
        if len(found) > 1:
            print(f"  提示：dist/ 下有 {len(found)} 个 wheel，检查最新的 {wheel.name}")
    if not wheel.exists():
        die(f"找不到文件：{wheel}")

    text, content_type = load_description(wheel)
    print(f"  产物        : {wheel.name}")
    print(f"  Content-Type: {content_type}")
    print(f"  描述长度    : {len(text)} 字符")

    if content_type != "text/markdown":
        # 非 Markdown 的描述交给 twine check 就够，这里不重复造轮子
        print(f"  [跳过] content-type 不是 text/markdown，渲染检查不适用")
        return 0

    # 后端缺失时 render() 会返回 None —— 那长得和"README 坏了"一模一样。
    # 不先分辨清楚，就会把人引向错误的方向。
    try:
        import comrak  # noqa: F401
    except ImportError:
        die(
            "缺少 Markdown 渲染后端。装它：\n"
            "    pip install \"readme_renderer[md]\"\n"
            "（不装的话 readme_renderer 会静默返回 None，看起来就像 README 渲染失败）"
        )

    from readme_renderer.markdown import render

    html = render(text)
    if html is None:
        die("渲染失败 —— PyPI 会直接拒收这个包")
    print(f"  渲染        : 成功，HTML {len(html)} 字符")

    # PyPI 不解析相对路径：图片会破、链接会 404，而渲染本身不会报错，
    # 所以这两条只能自己查。
    images = re.findall(r'<img[^>]+src="([^"]*)"', html)
    links = re.findall(r'<a[^>]+href="([^"]*)"', html)
    print(f"  图片        : {len(images)} 个")
    print(f"  链接        : {len(links)} 个")

    problems = problems_in(html)
    if problems:
        for p in problems:
            print(f"\n  ✗ {p}", file=sys.stderr)
        die("项目描述里还有相对地址。改成绝对地址后重新打包。")

    # 表格和代码块是 README 的主要结构，渲染丢了说明后端有问题
    print(f"  结构        : <h2>x{html.count('<h2')}  <table>x{html.count('<table')}  <pre>x{html.count('<pre')}")
    print("\n  ✅ 项目描述可以被 PyPI 正常渲染\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
