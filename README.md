# optiland-zh

> vibe coding

**把 Optiland 的界面变成中文。** 它不改 Optiland 的代码，只在程序启动的时候把界面上的
英文换成中文 —— 所以 Optiland 本体要另外装（见下面「安装」）。

[English](https://github.com/Kino2315/optiland-zh/blob/main/README.en.md) | 中文

![效果](https://raw.githubusercontent.com/Kino2315/optiland-zh/main/docs/screenshot-zh.png)

> 想看这个项目的**来龙去脉和技术看点**（文字即逻辑键的陷阱、六个实测踩坑、
> 覆盖率数字该怎么审查），读 [项目介绍](https://github.com/Kino2315/optiland-zh/blob/main/docs/intro.md)。

## 这是什么

[Optiland](https://github.com/optiland/optiland)（下面简称**上游**）是一个功能完整的
开源光学设计软件（序列/非序列光线追迹、优化、公差、MTF、Zemax 文件导入……），
自带一个 Qt 图形界面。但它**只有英文，也没有任何多语言开关**。

这个包**不改上游的代码**，而是在程序启动的时候把界面文字替换掉。所以：

- **`pip install -U optiland` 不会把汉化冲掉。** 汉化不在上游的文件里，升级动不到它。
- **但升级仍然可能让汉化失效。** 替换靠的是"记住上游每一个控件叫什么名字"；
  上游哪天改了名字，那一处就会悄悄变回英文，**而且不会报错**。
  升级后跑一次 [`optiland-zh --self-test`](#检查汉化有没有出问题) 就知道有没有出问题。

## 安装

### 一、普通用户

```sh
pip install "optiland[gui]"      # ① Optiland 本体（下载约 440 MB）
pip install optiland-gui-zh      # ② 本汉化包（50 KB）
```

**两条都要写。** 本包不声明 `optiland` 依赖 —— 那样会强制拉一份完整的 Qt 和 VTK，
和你已经装好的版本打架。

装完会有两个启动命令，用途不同：

| 命令 | 控制台窗口 | 用在哪 |
|---|---|---|
| `optiland-zh` | 有 | 终端里用。出错时能在窗口外看到诊断信息 |
| `optiland-zh-gui` | 没有 | 双击用。不弹黑框，出错时弹对话框 |

### 桌面图标

```sh
optiland-zh --install-shortcut
```

会在桌面新建一个 **Optiland 中文版** 快捷方式，双击直接以中文界面启动。
默认指向**不带控制台**的那个入口（也就是 `optiland-zh-gui`）。

| 想要什么         | 命令                                             |
|--------------|------------------------------------------------|
| 新建到别的目录      | `optiland-zh --install-shortcut --shortcut-dir <目录>` |
| 带控制台，方便看报错   | `optiland-zh --install-shortcut --console-shortcut` |
| 删掉它          | `optiland-zh --uninstall-shortcut`                  |

`--uninstall-shortcut` **只删本工具自己建的那一个名字**，不会去动你手工做的快捷方式。

> 图标文件生成在 `%LOCALAPPDATA%\optiland-zh\`。

### 二、从源码安装

想阅读代码或想做贡献时：

```sh
pip install "optiland[gui]"
git clone https://github.com/Kino2315/optiland-zh
cd optiland-zh
pip install .
```

### 三、开发

```sh
git clone https://github.com/Kino2315/optiland-zh
cd optiland-zh
pip install -e ".[dev]"     # -e 是 editable：改完代码立刻生效，不用重装
pytest -q
```

### 只装了汉化包、没装上游？

你会看到这段提示：

```
[optiland-zh] 找不到：PySide6、optiland_gui

本包只是汉化层，不含 Optiland 本体。请先装上游：

    pip install "optiland[gui]"

（汉化包刻意不声明 optiland 依赖，免得和你已经装好的 Qt 版本打架。）
```

照着做即可。`--list-languages` 和 `--help` 不需要 Qt。

## 使用

```sh
optiland-zh
```

这一条命令会装上汉化，然后拉起 Optiland GUI。

也可以加参数：

```sh
optiland-zh --list-languages    # 列出随包分发的语言
optiland-zh -l zh_CN            # 指定界面语言（-l 是 --language 的简写）
optiland-zh -c my.json          # 换用自己写的词库（-c 是 --catalog 的简写）
optiland-zh --no-locale         # 只换文字，不改动 Qt 的 locale
```

另外还有三条**检查工具**（`--self-test` / `--coverage` / `--audit`），
平时用不上，见下面的[检查汉化有没有出问题](#检查汉化有没有出问题)。

在自己的脚本里使用（`QApplication` 是 Qt 的程序对象，汉化补丁必须赶在它建立之前装上）：

```python
import optiland_zh

optiland_zh.install()  # 必须早于 QApplication
from optiland_gui.run_gui import main
main()
```

> **为什么不直接改源码**  
> 改 `site-packages` 里的文件最简单，但 `pip install -U optiland` 一升级就全没了，而且没法作为独立项目分发。
> 所以这里的做法是：**在文字进入 Qt 之前把它换掉**。补丁通过赋值的形式打在 PySide6 的绑定类型上。

## 词库

每种语言对应一个 JSON 文件，放在 `src/optiland_zh/catalogs/`。（目前只有简体中文）

大意是这样（实际文件里还有 `display_name`、`version` 等字段，所以**加语言时直接复制现成的文件**，不要照着下面从零写）：

```json
{
  "language": "zh_CN",
  "entries": {
    "&File": "文件(&F)",
    "Lens Data Editor": "镜头数据编辑器"
  },
  "patterns": [
    {
      "match": "Field {0}: ({1}, {2})",
      "replace": "视场 {0}：({1}, {2})"
    }
  ]
}
```

动态消息用 `{0} {1}` 占位（写法和 Python 的 `str.format` 一样），运行的时候会被
实际的值填进去。程序启动时会把这些模板转换成匹配规则，用来认出界面上"拼出来"的文字。

### 贡献：加词条 / 加语言

1. 复制 `src/optiland_zh/catalogs/zh_CN.json`
2. 改 `language` / `display_name`
3. 翻译 `entries` 和 `patterns` 的 `replace`（**不要动 `match`**）
4. 跑 `optiland-zh -l <你的语言> --coverage` 看覆盖率。

详见 [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md)

#### 更新后补充

Optiland 升级之后，界面里可能多出一些英文 —— 新功能带来的新文字，词库里还没有。
**这多半不是汉化坏了，只是还没人翻** —— 但别猜，查一下：

```sh
optiland-zh --lookup "那句英文"
```

它会把 `&` 和结尾的省略号忽略掉，所以**照着屏幕上看到的原样打**就行。（屏幕上
可能是 `Save System`，词库里的键是 `&Save System`，你不需要知道这件事。）

- **查得到** → 词库里有译文、界面上却还是英文 → **补丁没拦住那个控件** → 要改引擎，
  不是加词条。
- **查不到** → **还没人翻** → 往下看。

补词条是**贡献者**（clone 了仓库的人）的事。**普通用户不用管** —— 你就算改了
`site-packages` 里那份词库，下次 `pip install -U optiland-gui-zh`（升级汉化包）
也会把它覆盖掉。想确认"补丁有没有失效"（那才叫坏了）是另一回事，跑
[`optiland-zh --self-test`](#检查汉化有没有出问题)。

**贡献者：先看看缺哪些**

```sh
optiland-zh --extract --diff src/optiland_zh/catalogs/zh_CN.json
```

`--extract` 把**当前环境里装着的** `optiland_gui` 扫一遍，挑出所有"像是界面文字"的
字符串；`--diff` 再拿这些结果和你给的那份词库比对，**只列出词库里还没有的**，
并按源文件分组：

```
扫描: .../site-packages/optiland_gui
  静态候选  : 312
  动态模式  : 72
  跳过(内部): 335

未翻译: 2 条（已翻译 508 条）

  ── custom_title_bar.py (1) ──
     Optiland

  ── python_terminal.py (1) ──
     Cascadia Code
```

> **那两个数口径不同，不是一回事：**
> `静态候选 312 + 动态模式 72 = 384` 是**从源码里扫出来的**；
> `已翻译 508` 是**词库自己的大小**（436 条词条 + 72 条动态规则）。
> 分母不一样，别拿来相减。

**关于目录和路径，有三件事容易搞混：**

1. **为什么要"在仓库根目录运行"** —— 只是因为命令末尾那个
   `src/optiland_zh/catalogs/zh_CN.json` 是按仓库的目录结构写的相对路径，
   换个目录就找不到这个文件。把它换成绝对路径，在哪儿跑都行。
2. **`--diff` 要指仓库里那份词库**（也就是你正要改的那一份），**不是**
   `site-packages` 里那份安装副本 —— 否则你就是拿"装出来的旧词库"去比
   "装出来的界面"，比出来的结果对改词条没有意义。
3. **它扫描的对象是"当前环境里装着的 `optiland_gui`"，不是仓库里的代码。**
   这一点跟你在哪个目录无关。

**它靠什么分辨哪些字符串不该翻**

用的是 Python 的 **AST（抽象语法树）**：先把 `.py` 文件解析成语法结构，再在结构上
找字符串，而不是拿正则扫文本。所以下面这些**根本不进候选**：

- `setObjectName("AnalysisPanel")` 这种控件内部名字
- 文档字符串
- `print()` / `logger.debug()` 这类控制台输出
- 样式表（QSS）、快捷键（`Ctrl+Q`）、配置键（`Layouts/Config`）
- 示例代码片段

**但还有第二道闸，那一道靠人判断。** 上面的清单只管"根本不进候选"；进了候选的里面，
仍然有 `Cascadia Code`（字体名）、`Optiland`（品牌名）这种**本来就不该翻**的 ——
它们会一直留在"未翻译"清单里，**这是正常的，不用管**。

补完之后跑一次 `optiland-zh --coverage`，看数字涨了没有。如果你是按上面「三、开发」
那节用 `pip install -e ".[dev]"` 装的，改完词库立刻生效，不用重装；普通安装的话
重新 `pip install .` 一次。

## 检查汉化有没有出问题

这三条平时用不上。**界面上出现英文、或者 Optiland 升级之后**，才需要用。

```sh
optiland-zh --self-test   # 我翻过的地方，有没有失效
optiland-zh --coverage    # 词库里有没有漏翻的
optiland-zh --audit       # 界面上实际显示出来的文字，逐条核对
```
**`--self-test` 检查「我已经翻译过的地方，有没有失效」。**

汉化的做法是：程序运行时把界面文字替换掉。具体说，它会记住 Optiland 里每一个控件
叫什么名字，在文字显示到屏幕上之前换成中文。**如果 Optiland 升级后改了某个控件的
名字，这个替换就会失效 —— 而且不会报错**，界面上悄悄变回英文。

这个命令会挑 7 个有代表性的地方实际跑一遍。一切正常时是这样的：

```
[OK  ] 'Lens Data Editor' -> '镜头数据编辑器'
[OK  ] 'Run Analysis' -> '运行分析'
[OK  ] 'Optiland GUI' -> 'Optiland 图形界面'
[OK  ] '&File' -> '文件(&F)'
[OK  ] 'Spot Diagram' -> '点列图'
[OK  ] 回译 currentText() -> 'Spot Diagram' (应为 'Spot Diagram')
[OK  ] findText('Spot Diagram') -> 0 (应为 0)

自检全部通过。
```

哪一项失效了，那一行就会变成 `[FAIL]`，最后还会告诉你「自检失败 1 项: …」。

**`--coverage` 检查「词库里有没有漏翻的」。**

Optiland 每次升级都可能多出新的界面文字。这个命令扫描 Optiland 的源代码，数出已经
翻了多少条、还剩多少条没有，并且把没翻的点名列出来：

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

**`--audit` 检查「界面上到底还有没有英文」。**

前面两个查的是「词库」和「补丁」，这一个查的是**实际显示出来的文字**。它会把
Optiland 真正的主窗口整个构造出来（用 Qt 的离屏模式，窗口不会显示到屏幕上），
然后走遍整棵控件树，把每一处文字都抓出来和词库对一遍 —— **包括没有展开的菜单、
没有点开的标签页**。这比人眼看截图可靠：截图只能看到当前这一屏。

它跑完会打印：

```
窗口树里的文字节点: 1082
  已覆盖: 1047  (96.8%)
  未覆盖: 35

判定分档（已覆盖按强度从高到低，缺口在后）:
    974  exact-value                文字正好等于词库里的某条译文
     30  cjk-only                   无任何拉丁字母 —— 已译完，确定
     43  cjk-mixed                  中英混合：还剩快捷键字母或专有名词，逐条可查
     35  MISS:not-translatable      本就是数字/objectName/第三方标识符

严格口径（只认 exact-value，不含 cjk-only / cjk-mixed）: 974 / 1082 = 90.0%
真缺口（补丁没生效 + 仍是英文原文）: 0
```

**这里面该看哪个数字：**

- **看「真缺口」是不是 0。** 它数的是「词库里有译文、但补丁没生效」加上「仍然是英文
  原文」—— **该翻而没翻的**。是 0 就说明汉化是好的。
- **「未覆盖」那 35 条不是问题。** 它们是 `QuickActionsToolbar` 这种控件内部名字、
  `BFGS` 这种 scipy 算法名、序号、装饰符 —— **本来就不应该翻译**。
- **别被两个百分比绕进去。** 96.8% 和 90.0% 量的是同一件事，只是口径不同：前者把
  「看着就是中文」的也算进去，后者只认和词库逐字符相等的。**判断汉化好坏看「真缺口」，
  不用纠结这两个数。**

**想看看某一档具体是哪些？**

```sh
optiland-zh --audit --rule cjk-mixed
```

它会把那一档的节点逐条列出来，格式是「控件类型 / 来源 / 文字」：

```
=== 判据 cjk-mixed 命中的节点（43 条去重）===
    ActionTip  QMenu      文件(F)
    ComboItem  QComboBox  通用 (scipy.minimize)
    ...
```

`--rule` 可以填这 6 个值之一：

```
exact-value              cjk-only                 cjk-mixed
MISS:patch-not-fired     MISS:still-translatable  MISS:not-translatable
```

名字打错会当场报错，不会静默返回 0 条。

**三个百分比不是一回事，别混：**

| 数字 | 来自 | 量的是什么 |
|---|---|---|
| **99.5%** | `--coverage` | 上游源码里能提取到的字符串，翻了多少 |
| **96.8%** | `--audit` 的「已覆盖」 | 界面上实际渲染出来的文字，有多少已经是中文 |
| **90.0%** | `--audit` 的「严格口径」 | 同上，但只认和词库逐字符相等的 |

它们**本来就不该相等**：第一个按源代码文件算，后两个按运行时控件算 —— 同一个字符串
可能出现在几十个控件上；反过来，运行期动态拼出来的文字在源码里根本不存在。

**两份「没翻」的清单也不是一回事：**

- `--coverage` 列出的「未翻译的静态条目」= 源码里有、但词库里查不到的字符串。
  **里面混着本来就不该翻的**（比如字体名 `Cascadia Code`）。
- `--audit` 的「未覆盖: 35」= 界面上渲染出来的文字里，词库查不到的那些。
  **这 35 条全都是不需要翻译的。**
- `--audit` 的「**真缺口**」= 该翻却没翻的。**这个才是 0 就说明汉化没问题。**

## 已知限制

- **绘图中的文字无法翻译。** 窗口标题（如 `System: Default System (2D)`）
  是 matplotlib 画的，不是 Qt 控件，本方案的补丁处理不到。
  需要 matplotlib 自己的翻译机制，暂未实现。
- **只覆盖 Optiland 的界面。** 第三方控件（Jupyter 控制台的右键菜单等）
  能翻的部分靠 Qt 通用补丁顺带覆盖，其余依赖它们各自的本地化机制。
- **PySide6 版本差异。** 个别类在不同版本里位置不同（`QStandardItem` 在
  `QtGui` 而非 `QtWidgets`），引擎遇到找不到的类会跳过，
  对应控件则不汉化。

## 翻译上游项目使用的术语中英对照

| 英文                                    | 中文                   |
|---------------------------------------|----------------------|
| Lens Data Editor                      | 镜头数据编辑器              |
| Aperture / Field / Wavelength         | 孔径 / 视场 / 波长         |
| Radius / Thickness / Material / Conic | 半径 / 厚度 / 材料 / 圆锥系数  |
| Stop / Sag / Semi-Diameter            | 光阑 / 矢高 / 半口径        |
| Spot Diagram / Ray Fan                | 点列图 / 光线扇形图          |
| OPD / MTF / PSF                       | 光程差 / 调制传递函数 / 点扩散函数 |

## 许可

MIT，见 [LICENSE](https://github.com/Kino2315/optiland-zh/blob/main/LICENSE)。

上游 [Optiland](https://github.com/optiland/optiland) 同为 MIT
（Copyright © 2024 Kramer Harrison）。本项目通过运行期进行补丁工作，不分发也不修改
其源码。第三方组件与术语来源的说明见 [NOTICE.md](https://github.com/Kino2315/optiland-zh/blob/main/NOTICE.md)。

## 贡献

见 [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md)。可做 **新增语言** 和 **补充词条** 的贡献。