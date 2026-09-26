# optiland-zh  
vibe coding

**Optiland GUI 的简体中文汉化包。** 运行期翻译层。
这是一个补丁，所以你仍然需要下载 Optiland 的本体

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

**启动：**

```sh
optiland-zh       # 在终端里用；出问题能在窗口外面看到报错信息
optiland-zh-gui   # 双击用；不会弹出黑色的控制台窗口
```

**检查工具** —— 打印完结果就退出，不会打开界面：

```sh
optiland-zh --list-languages   # 列出随这个包一起分发的语言
optiland-zh --self-test        # 汉化补丁有没有真的生效
optiland-zh --coverage         # 词库覆盖了多少条界面文字
optiland-zh --audit            # 界面上实际显示出来的文字，逐条核对
```

这三条平时用不上。**界面上出现英文的时候，或者 Optiland 升级之后**，才需要用。
它们各自管什么：

**`--self-test` —— 我翻过的地方，有没有失效**

汉化的做法是：在程序运行时把界面文字替换掉。具体说，它会记住 Optiland 里
每一个控件叫什么名字，在文字显示到屏幕上之前换成中文。

**如果 Optiland 升级后改了某个控件的名字，这个替换就会失效 —— 而且不会报错**，
界面上悄悄变回英文。`--self-test` 会挑 7 个有代表性的地方实际跑一遍，
告诉你哪一项没有生效：

```
[FAIL] 'Spot Diagram' -> 'Spot Diagram'    ← 这一项没生效，文字没被换掉
自检失败 1 项: Spot Diagram
```

**`--coverage` —— 词库里有没有漏翻的**

Optiland 每次升级都可能多出新的界面文字。这条命令会扫描 Optiland 的源代码，
数出有多少条文字已经在词库里、还剩多少条没有，并且把没翻的点名列出来：

```
词库: 简体中文 (zh_CN)
  静态界面文字 :  310 / 312   99.4%
  动态消息模板 :   72 / 72   100.0%
  合计         :  382 / 384   99.5%

未翻译的静态条目（前 30 条）:
    'Cascadia Code'
    'Optiland'
```

最后这两条是字体名和品牌名，**本来就不应该翻译**。

**`--audit` —— 界面上到底还有没有英文**

前面两条查的是「词库」和「补丁」。这一条查的是**实际显示出来的文字**。

它会把 Optiland 真正的主窗口整个构造出来，然后走遍整棵控件树，把界面上每一处
文字都抓出来，逐条和词库比对 —— **包括没有展开的菜单、没有点开的标签页。**

这比人眼看截图可靠：截图只能看到当前这一屏。

> 「离屏」是指 Qt 的一种运行方式：界面照常构造，但不显示到屏幕上。
> 所以这条命令在终端里能跑，在没有显示器的服务器上也能跑。

**也可以在自己写的脚本里调用：**

```python
import optiland_zh

optiland_zh.install()                    # 必须在创建 QApplication 之前调用
from optiland_gui.run_gui import main
main()
```

## 常见问题

**提示找不到 `PySide6` 或 `optiland_gui`**

只装了汉化包，没装本体。`pip install "optiland[gui]"` 即可。

**想要桌面图标**

`optiland-zh --install-shortcut` 创建；不想要了用 `optiland-zh --uninstall-shortcut` 删除。

**想换语言，或者加一种语言**

词库是 JSON，加语言不需要懂 Python。见 [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md)。

## 它做了什么

Optiland 自带 Qt 图形界面，但只有英文，也没有语言开关。本包在运行期给
PySide6 的绑定打补丁，在文字进入 Qt 之前把它换掉——所以
`pip install -U optiland` 之后汉化依然有效。

有两件事值得说明：

**界面是中文，程序内部读到的仍然是英文。** GUI 里有 18 处 `currentText()`
拿控件文字当逻辑键，比如用下拉框显示的分析名去查注册表。如果只做单向翻译，
这些功能会**静默失效**。
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

下面的命令都在**仓库根目录**运行（路径是相对的）：

| 想做什么 | 怎么做 |
|---|---|
| **补词条** | `optiland-zh --extract --diff src/optiland_zh/catalogs/zh_CN.json` 列出还缺什么，把译文加进 `entries` |
| **加一种语言** | 复制 `catalogs/zh_CN.json`，改 `language` 和 `display_name`，翻译 `entries` 的值以及 `patterns` 里的 `replace`（`match` 不能动） |
| **改引擎** | 界面上还有英文时，先用 `optiland-zh --lookup "那句英文"` 查它在不在词库里 —— 查得到说明补丁没拦住（引擎问题），查不到说明还没人翻（词条问题）。确认是引擎问题再用 `optiland-zh --audit` 定位属于哪类拦截点，然后按 [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md) 的「改引擎」一节动手 |

改完跑一遍：

```sh
pytest -q
optiland-zh --self-test
```

## 许可

MIT，见 [LICENSE](https://github.com/Kino2315/optiland-zh/blob/main/LICENSE)。
上游 [Optiland](https://github.com/optiland/optiland) 同为 MIT；第三方组件说明见
[NOTICE.md](https://github.com/Kino2315/optiland-zh/blob/main/NOTICE.md)。
