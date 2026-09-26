"""文档之间的一致性检查。

同一份内容被抄到两个文件里时，靠测试盯着它们别各改各的 —— 和版本号散在三处
是一个道理（那个见 `test_packaging.py::TestVersionConsistency`）。

现在盯着：**术语中英对照表**（`README.md` 与 `CONTRIBUTING.md`）。

为什么要盯：这张表是这个项目的翻译标准。标准一旦分叉，词库本身就会跟着不一致，
而词库是这个项目唯一的核心资产。
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# (文件, 表格前面那句话里的片段) —— 用它把表定位出来
TABLE_SOURCES = [
    (ROOT / "README.md", "术语中英对照"),
    (ROOT / "CONTRIBUTING.md", "术语请对齐"),
]

HEADER_CELLS = {"英文", "English"}


def read_table(path: Path, hint: str) -> list[tuple[str, str]] | None:
    """读出 ``hint`` 那句话之后的第一个两列表格。

    找不到文件、找不到 hint、或者后面没有表格，都返回 ``None``。
    """
    if not path.exists():
        return None

    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if hint in line)
    except StopIteration:
        return None

    rows: list[tuple[str, str]] = []
    for line in lines[start:]:
        if not line.startswith("|"):
            if rows:
                break  # 表格结束
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        # 跳过 |---|---| 这种分隔行
        if set(cells[0]) <= {"-", ":", " "}:
            continue
        # 跳过表头
        if not rows and cells[0] in HEADER_CELLS:
            continue
        rows.append((cells[0], cells[1]))

    return rows or None


def test_terminology_table_is_in_sync() -> None:
    """README 和 CONTRIBUTING 里的术语表必须一字不差。

    只找到一处时跳过 —— 说明还没抄第二份，没什么可比的。
    """
    found = [(path.name, read_table(path, hint)) for path, hint in TABLE_SOURCES]
    present = [(name, table) for name, table in found if table]

    if len(present) < 2:
        where = "、".join(name for name, _ in present) or "任何文件"
        pytest.skip(
            f"只在 {where} 里找到术语表，没有第二份可比。"
            "等 README 也加上之后，这条测试会自动开始生效。"
        )

    (name_a, table_a), (name_b, table_b) = present[0], present[1]
    if table_a == table_b:
        return

    only_a = [row for row in table_a if row not in table_b]
    only_b = [row for row in table_b if row not in table_a]
    raise AssertionError(
        f"{name_a} 和 {name_b} 的术语表不一致 —— "
        "同一份内容抄在两处，改一处就必须改另一处。\n"
        f"  只在 {name_a} 里：{only_a}\n"
        f"  只在 {name_b} 里：{only_b}"
    )
