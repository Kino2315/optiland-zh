# 把 Optiland 的图形界面变成中文，顺便踩了六个不看源码就发现不了的坑

> 一份关于 `optiland-zh` 的介绍。项目地址见文末。

![汉化后的界面](https://raw.githubusercontent.com/Kino2315/optiland-zh/main/docs/screenshot-zh.png)

## 先说这个东西是什么

[Optiland](https://github.com/optiland/optiland) 是这两年开源圈里少见的认真做的光学设计软件。它不是玩具——序列和非序列光线追迹、非球面和自由曲面、点列图、光线扇形图、OPD、PSF、MTF、Zernike 波前、梯度优化和全局优化、公差分析和蒙特卡洛、材料库直连 refractiveindex.info、多层膜合成，还能直接读写 Zemax 的 `.zmx` 文件。

说人话：**它能干很多 Zemax 能干的事，而且免费、纯 Python、`pip install optiland` 就能装。**

它甚至自带一个 Qt 图形界面，长得跟 Zemax 一个路子——Lens Data Editor、Layout 视图、Analyses 面板、Aperture/Fields/Wavelengths 系统属性，连"LDE"这个名字都直接沿用。

**但它是英文的，而且没有任何语言开关。**

我翻了源码确认过，不是"漏做了"：

- `self.tr()` 出现 **0 次**
- 没有 `.qm` / `.ts` 翻译文件
- 所有界面文字都是硬编码字面量，比如 `menu_bar.addMenu("&File")`
- 它甚至**主动把语言钉死**在英文：

```python
QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
```

所以想要中文，只能自己动手。`optiland-zh` 就是干这个的。

## 为什么不能直接改源码

最省事的做法是把 `site-packages/optiland_gui/` 里的英文字符串挨个换成中文。五分钟能搞定。

但有两个问题：

1. **`pip install -U optiland` 一升级就没**，而且每次升级都得重打补丁。
2. **没法作为独立项目分发**。你总不能让人家下载你魔改过的 Optiland。

所以这里的做法是：**一行源码都不改，在运行期把文字换掉。**

具体讲，在文字**进入 Qt 之前**拦截。PySide6 是 Shiboken 生成的绑定类型，我实测确认它们允许在运行期赋值——`QLabel.__init__` 都能换掉：

```python
QLabel.__init__   可赋值
QPushButton.setText   可赋值
QMenu.addMenu   可赋值
QComboBox.addItem   可赋值
```

这条路走得通，于是有了整个项目的基础。

## 真正的难点：文字就是逻辑键

这是我一开始完全没想到的，也是整个项目最值得讲的部分。

汉化 Qt 应用有个隐藏陷阱：**程序会拿控件的显示文字去做逻辑判断。**

Optiland GUI 里有 **18 处**这样的代码：

```python
self.on_analysis_type_changed(self.analysisTypeCombo.currentText())
```

这一句是拿下拉框里**显示的文字**，去查"分析类注册表"。

于是你天真地把 `"Spot Diagram"` 翻成 `"点列图"`，`currentText()` 就返回 `"点列图"`，注册表查不到——**整个分析功能静默失效**。不报错、不崩溃，就是点了没反应。

`QLineEdit` 更隐蔽。面型编辑是这么写的：

```python
new_type = self.type_edit.text()                            # lens_editor.py:205
if new_type.lower().strip() in self.get_available_surface_types():
```

后面比的是**英文**面型表。只做单向翻译，`"标准" in ["standard", ...]` 是 `False`，改面型会静默失败。

这个坑要是没查出来，我写的东西会以一个"看起来能用、关键时刻掉链子"的形态发出去，而且这种 bug 极难被用户定位。

### 解法：双向翻译

所以这个项目的核心不是"替换字符串"，而是**双向**的：

| 方向 | 做法 |
|---|---|
| 文字**进入** Qt | 英译中（构造器 / `setText` / `addItem` / `addMenu` / …） |
| 原文**存起来** | 下拉框存进该项的 `userData`（自定义角色）；输入框存进 Qt 动态属性 |
| 逻辑**读出来** | `currentText()` / `QLineEdit.text()` 还原成英文 |
| 按文字**查找** | `findText()` / `setCurrentText()` 的查询词先中译英 |

界面是中文，程序内部看到的仍然是英文。两边都不坏。

**为什么用 `userData` 而不是反向查表？** 因为反向查表有歧义——如果两个英文词都译成同一句中文，就不知道该还原成哪个。把原文存在控件自己身上，一对一，不会有这个问题。

### 一个反直觉的细节

`itemText()` 我**故意没有**回译。

因为 Qt 拿 `itemText()` 去渲染下拉列表——回译了，列表就显示英文，等于白干。

那程序里那唯一一处调用 `itemText()` 怎么办？去看了一眼：它是把结果喂给 `setCurrentText`，而 `setCurrentText` 那条路径本来就是通的。所以只要不动它，整个链路自洽。

**这类决定没法靠规则推导，只能一行一行读调用点。**

## 一路踩到的坑

光拦 `QLabel` 是远远不够的。下面每一条都是实测发现的，不是推演出来的。

### 一、`QFormLayout.addRow("标签", 控件)` 的标签，Python 层根本看不到

Qt 的 `addRow` 接受一个字符串当标签，它会**在 C++ 内部**顺手建一个 `QLabel`。

我们所有的补丁都打在 Python 绑定层——那次构造根本没经过 Python。

结果：**19 个表单标签全部漏译**，包括 `Aperture Type:`、`Field Type:`、`Surface Index:`、`Phase X (°):`。

修法是补丁打在 `addRow` 本身上。

### 二、`QDockWidget("标题", parent)` 不在白名单里

`Script Editor` 和 `Console` 一直是英文。查了半天，它们来自：

```python
dock = QDockWidget("Script Editor", self)
```

我最初的构造器白名单只有 `QLabel` / `QPushButton` / `QAction` 这些，**没有 `QDockWidget`**。

教训：判断一个类该不该进白名单，看它的 `__init__` 有没有"一上来就是标题"的位置参数。`QWidget` / `QMainWindow` / `QDialog` / `QTabWidget` 第一个参数是父控件，加了也没用。

### 三、对话框上的 OK / Cancel，Optiland 源码里压根没有

那些字是 **Qt 自己**产生的。你在 Optiland 源码里怎么搜都搜不到。

解法不是补丁，是加载 Qt 自带的中文翻译文件：

```python
translator.load("qtbase_zh_CN", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
```

好消息是 PySide6 自带这些 `.qm`（`qtbase_zh_CN.qm`，147KB），不用额外下载。

**顺带一个坑**：`QTranslator` 必须留住引用，被垃圾回收了 Qt 的文字立刻变回英文。

### 四、优化器下拉项带前导空格

`" Least Squares"` —— 那个空格是为了在下拉列表里做视觉对齐。

词库里当然写的是 `"Least Squares"`，精确匹配不上。

修法是让词库匹配**容忍首尾空白**，并且回填时把原来的缩进还回去，免得破坏对齐。

### 五、`Toggle {0}` 会拼出「显示/隐藏 Analysis」这种半中半英

有一类消息是运行期拼的：

```python
menu.addAction(f"Toggle {dock_name}")
```

动态规则命中后，`{0}` 捕获到的是 `"Analysis"` 这个英文词，直接回填就是「显示/隐藏 Analysis」。

修法是：**动态规则捕获到的内容，再过一遍静态词条**。

### 六、提取器的过滤质量，直接决定工作量

汉化完不是结束——上游一升级，新增的界面文字就漏译了。所以需要工具把待翻译的字符串扫出来。

第一版我写得很粗暴，结果抓出 **857 条**候选。打开一看大半是噪音：

- 文档字符串（`"""Updates the theme of..."""`）
- `setObjectName("AnalysisPanel")` 里的**内部标识符**——这个最危险，翻译了会破坏样式表和控件查找
- `print()` / `logger.debug()` 的控制台输出
- 样式表（QSS）
- 快捷键（`Ctrl+Q`）
- 配置键（`Layouts/Config`）
- 示例菜单往终端里插的 **Python 代码片段**——翻译了直接把代码改坏

改成**上下文感知**（用 AST 看每个字符串是传给谁的）+ 排除文档字符串之后，压到 **312 条**，全是真要翻的。差 **2.7 倍**。

这里还踩了一个反向的坑：我一度把 `_create_dock` 加进了"这是界面文字"的白名单，结果它的第二个参数是 objectName：

```python
_create_dock(widget, "LensEditorDock", "Lens Data Editor")
#             ^^^^ objectName      ^^^^ 真正的标题
```

差一点就给 `LensEditorDock` 写了中文译文。**加白名单之前得看函数签名，不能只看函数名像不像在设文字。**

## 怎么证明它真的成了

我不想只给一个"汉化完成"的结论，所以做了三个层次的验证工具。

### 1. 自检（不需要开窗口）

```sh
optiland-zh --self-test
```

七项断言：构造器、`setText`、菜单、下拉框显示中文**且** `currentText()` 回译成英文、`findText` 能找到。

### 2. 静态覆盖率

```sh
optiland-zh --coverage
```

源码里扫出来的字符串，翻了多少。

```
静态界面文字 :  310 / 312   99.4%
动态消息模板 :   72 / 72    100.0%
合计         :  382 / 384   99.5%
```

没翻的两条是 `Cascadia Code`（字体名，翻了会换字体）和 `Optiland`（品牌名）——**故意的**。

### 3. 动态审计（最硬的证据）

```sh
python -m optiland_zh.audit
```

它把真实的 MainWindow 建出来（离屏、不弹窗），遍历整棵控件树，把界面上**实际存在的每一处文字**都抓出来，逐个和词库比对。

```
窗口树里的文字节点: 1082
  已覆盖: 1047  (96.8%)
  未覆盖: 35

判定分档（强度从高到低）:
    974  exact-value           文字正好等于词库里的某条译文
     73  cjk-heuristic         含中文即算已汉化（宽松）
     35  MISS:not-translatable 本就是数字/objectName/第三方标识符

真缺口（补丁没生效 + 仍是英文原文）: 0
```

**为什么要分档？** 单看"96.8%"没法判断里面有多少是靠宽松规则凑的。一个不可拆解的数字不算证据。

`exact-value` 是硬证据（逐字符相等）。`cjk-heuristic`（含中文就算汉化）覆盖的是动态规则拼出来的结果，它们不可能原样出现在词条表里——但这条规则**理论上也可能把漏译误判成已覆盖**，所以必须单独计数、单独核查：

```sh
python -m optiland_zh.audit --rule cjk-heuristic
```

73 条我逐条看过，全部属实：Qt 自动派生的 tooltip（`文件(&F)` → `文件(F)`）、动态消息（`显示/隐藏 分析`）、带缩进的下拉项。**没有一条误判。**

真正该盯的数字是 **`真缺口 = 0`**：没有任何一处"词库有译文却没生效"，也没有任何一处"仍是英文原文"。

剩下 35 条**本来就该是英文**：Qt 的 objectName（`QuickActionsToolbar`）、scipy 算法名（`BFGS` / `SLSQP` / `trust-constr`）、序号、品牌名、装饰符。

## 词库是数据，不是代码

所有译文放在 JSON 里，一种语言一个文件：

```json
{
  "language": "zh_CN",
  "entries": {
    "&File": "文件(&F)",
    "Lens Data Editor": "镜头数据编辑器"
  },
  "patterns": [
    { "match": "Field {0}: ({1}, {2})", "replace": "视场 {0}：({1}, {2})" }
  ]
}
```

动态消息用 `{0} {1}` 位置占位，运行期编译成正则。这是刻意的设计——**比让译者去写 `(?P<n>.+?)` 友好得多，也不容易写错。**

**加一种语言不需要懂 Python**：复制 `zh_CN.json`，改 `language`，翻 `entries` 的值和 `patterns` 的 `replace`（`match` 绝对不能动），然后跑 `optiland-zh --coverage` 看数字。

## 为什么我要写这么多验证工具

因为"汉化完成"这句话本身没有信息量。

一个覆盖率数字如果是黑箱，你没法判断它是真的 96% 还是凑出来的 96%。所以我把审计工具做成**能自己交代数字来源**的：分档统计、逐条可查、口径可切换（`python -m optiland_zh.audit --rule <档位>`）。

**好的指标应该能在你怀疑它的时候，让你亲自去推翻它。**

## 现在的状态

| | |
|---|---|
| 词条 | 436 条静态 + 72 条动态模板 |
| 源码覆盖率 | 99.5% |
| 界面覆盖率 | 96.8%（真缺口 **0**） |
| 单元测试 | 34 项全通过 |
| 许可证 | MIT |
| 上游 | Optiland 0.6.2（MIT） |

## 已知限制（说清楚，不藏）

- **画在图里的文字够不到。** 绘图窗口标题（如 `System: Default System (2D)`）是 matplotlib 画的，不是 Qt 控件，补丁层碰不到。要处理得走 matplotlib 自己的 i18n 机制。
- **只覆盖 Optiland 的界面。** 第三方控件（Jupyter 控制台的右键菜单等）能翻的靠 Qt 通用补丁顺带覆盖，其余依赖它们自己的 i18n。
- **PySide6 版本差异。** 个别类在不同版本里位置不同（`QStandardItem` 在 `QtGui` 而不是 `QtWidgets`）。引擎遇到找不到的类会跳过而不是崩，对应控件则不汉化。

## 怎么用

```sh
pip install "optiland[gui]"
pip install optiland-gui-zh

optiland-zh
```

---

## 最后

这个项目真正的价值不在"把英文换成中文"。那部分用一天就能做完。

价值在于**把 Qt 汉化里那些只能靠实测撞出来的坑，一条条记录成了可复现的代码和文档**：文字即逻辑键、C++ 内部创建的控件、Qt 自带的翻译文件、提取器的过滤边界、以及"一个覆盖率数字该怎么被审查"。

如果你也在做类似的事——汉化一个没有 i18n 的 PySide6 应用——这里踩过的坑应该能帮你省掉大部分时间。

MIT 许可。补词条和加语言都不需要懂 Python，欢迎 PR。
