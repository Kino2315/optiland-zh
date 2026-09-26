"""optiland-zh —— Optiland GUI 的简体中文汉化层。

设计要点
--------
1. **不改上游源码。** 全部工作在运行期完成：在文字进入 Qt 之前把它换掉。
   所以 ``pip install -U optiland`` 之后汉化依然有效。
2. **词库是数据，不是代码。** 所有译文放在 ``catalogs/*.json``，社区可以直接
   提 PR 加词条、加语言，不需要碰 Python。
3. **可再提取。** ``optiland-zh --extract`` 能把新版 Optiland 里新增的
   界面文字重新扫出来，升级后按差集补译即可。

公开 API
--------
``install()``
    装上所有补丁。必须在创建 ``QApplication`` **之前**调用。
``uninstall()``
    还原，主要给测试用。
``translate(text)``
    翻译单个字符串，命不中就原样返回。
``load_catalog(language)``
    载入指定语言的词库。
"""

from __future__ import annotations

__version__ = "0.2.8"

from .catalog import Catalog, load_catalog
from .engine import install, is_installed, translate, uninstall

__all__ = [
    "__version__",
    "Catalog",
    "load_catalog",
    "install",
    "uninstall",
    "is_installed",
    "translate",
]
