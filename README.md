# optiland-zh  
vibe coding

**Optiland GUI 的简体中文汉化包。** 运行期翻译层，不修改上游源码。

![效果](https://raw.githubusercontent.com/Kino2315/optiland-zh/main/docs/screenshot-zh.png)

[English](https://github.com/Kino2315/optiland-zh/blob/main/README.en.md) | 中文 | [PyPI](https://pypi.org/project/optiland-gui-zh/)

## 快速开始

```sh
pip install "optiland[gui]" optiland-gui-zh
optiland-zh
```

两条 `pip` 都要写。本包刻意不声明 `optiland` 依赖——那样会强制拉一份完整的
Qt 和 VTK，和你已经装好的版本打架，所以 pip 不会替你带上它。

## 使用

```sh
optiland-zh                    # 启动（终端用，能看到诊断信息）
optiland-zh-gui                # 启动（双击用，不弹控制台）
optiland-zh --list-languages   # 列出可用语言
optiland-zh --self-test        # 离屏自检，不开窗口
optiland-zh --coverage         # 词库覆盖率报告
```

也可以在自己的脚本里调用：

```python
import optiland_zh

optiland_zh.install()                    # 必须早于 QApplication 创建
from optiland_gui.run_gui import main
main()
```

## 常见问题

**提示找不到 `PySide6` 或 `optiland_gui`**

只装了汉化包，没装上游。`pip install "optiland[gui]"` 即可。

**想要桌面图标**

`optiland-zh --install-shortcut`。不想要了用 `--uninstall-shortcut`。

**想换语言，或者加一种语言**

词库是 JSON，加语言不需要懂 Python。见 [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md)。

## 它做了什么

Optiland 自带 Qt 图形界面，但只有英文，也没有语言开关。本包在运行期给
PySide6 的绑定打补丁，在文字进入 Qt 之前把它换掉——所以
`pip install -U optiland` 之后汉化依然有效。

有两件事值得说明：

**界面是中文，程序内部读到的仍然是英文。** GUI 里有 18 处拿控件文字当逻辑键，
比如用下拉框显示的分析名去查注册表。如果只做单向翻译，这些功能会**静默失效**。
所以 `currentText()` 和 `QLineEdit.text()` 会把原文还给程序。

**Qt 在 C++ 里创建的控件也覆盖到了。** 比如 `QFormLayout.addRow` 的标签、
`QDockWidget` 的标题——这些控件的创建过程 Python 层看不到。Qt 自带的对话框按钮
（确定 / 取消 / 打开）则通过加载 `qtbase_zh_CN.qm` 解决。

详细的技术记录见 [项目介绍](https://github.com/Kino2315/optiland-zh/blob/main/docs/intro.md)。

## 已知限制

- 画在图表里的文字（matplotlib 绘图区标题）够不到
- 只覆盖 Optiland 自身的界面；第三方控件依赖它们各自的 i18n

## 贡献

三种贡献，按所需技能从低到高。**前两种不需要懂 Python。**

| 想做什么 | 怎么做 |
|---|---|
| **补词条** | `python -m optiland_zh.extract --diff src/optiland_zh/catalogs/zh_CN.json` 列出还缺什么，把译文加进 `entries` |
| **加一种语言** | 复制 `catalogs/zh_CN.json`，改 `language` 和 `display_name`，翻译 `entries` 的值以及 `patterns` 里的 `replace`（`match` 不能动） |
| **改引擎** | 界面上还有英文时，先用 `python -m optiland_zh.audit` 定位它属于哪类拦截点，再按 [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md) 的「改引擎」一节动手 |

改完跑一遍：

```sh
pytest -q
optiland-zh --self-test
```

## 许可

MIT，见 [LICENSE](https://github.com/Kino2315/optiland-zh/blob/main/LICENSE)。
上游 [Optiland](https://github.com/optiland/optiland) 同为 MIT；第三方组件说明见
[NOTICE.md](https://github.com/Kino2315/optiland-zh/blob/main/NOTICE.md)。
