# 贡献指南

三条路，按所需技能从低到高。

## 一、补词条（不需要懂 Python）

1. 跑一遍提取器看还缺什么（**在仓库根目录运行**，下面的路径是相对的）：

   ```sh
   python -m optiland_zh.extract --diff src/optiland_zh/catalogs/zh_CN.json
   ```

   它按源文件分组列出没翻译的字符串。`strings.json` 里每个词条还带**出现位置**
   （文件 + 行号），想确认上下文就去翻那一行。

2. 在 `src/optiland_zh/catalogs/zh_CN.json` 的 `entries` 里加一条：

   ```json
   "Analysis Settings": "分析设置"
   ```

3. 验证覆盖率涨了：

   ```sh
   optiland-zh --coverage
   ```

**术语请对齐 Zemax 中文版。** 新术语先查《光学名词》或 Zemax 中文界面，
不要自己造词。常用对照：

| 英文 | 中文 |
|---|---|
| Lens Data Editor | 镜头数据编辑器 |
| Aperture / Field / Wavelength | 孔径 / 视场 / 波长 |
| Radius / Thickness / Material / Conic | 半径 / 厚度 / 材料 / 圆锥系数 |
| Stop / Sag / Semi-Diameter | 光阑 / 矢高 / 半口径 |
| Spot Diagram / Ray Fan | 点列图 / 光线扇形图 |
| OPD / MTF / PSF | 光程差 / 调制传递函数 / 点扩散函数 |

### 什么不该翻

| 类型 | 例子 | 原因 |
|---|---|---|
| 字体名 | `Cascadia Code` | 翻了会换成别的字体 |
| 第三方算法名 | `BFGS`、`SLSQP`、`trust-constr` | 是 scipy 的标识符，中文界也照写 |
| Qt 内部标识符 | `QuickActionsToolbar` | objectName，翻了会破坏控件查找和样式表 |
| 品牌名 | `Optiland` | 产品名 |

### 翻译时要注意的地方

- **`&` 是快捷键标记**，中文惯例写成 `文件(&F)`，不要丢掉它。
- **`%s` / `%d` 是 printf 占位符**，必须原样保留、数量一致。
- **文件对话框过滤器**形如 `JSON Files (*.json);;All Files (*)`，
  只翻描述部分，`*.json` 和 `;;` 分隔符不能动。
- **HTML 标签**（`<b>` `<h3>`）要保留。

## 二、加一种语言（也不需要懂 Python）

1. 复制 `src/optiland_zh/catalogs/zh_CN.json`
2. 改名成目标语言代码（如 `zh_TW.json`、`ja_JP.json`）
3. 改 `language`（必须和文件名一致）和 `display_name`
4. 翻译 `entries` 的值，以及 `patterns` 里每条规则的 `replace`
   —— **`match` 字段绝对不能改**，它是匹配用的模板
5. 验证：

   ```sh
   optiland-zh --list-languages
   optiland-zh -l ja_JP --coverage
   optiland-zh -l ja_JP --self-test
   ```

`patterns` 用 `{0} {1}` 位置占位符，写法和 `str.format` 一样。
占位符的**数量和顺序**可以和 `match` 不同（比如中文语序不同），
但不能引用不存在的编号。

## 三、改引擎（需要懂 Python + Qt）

### 先读这两件事

1. **回译机制不能删。** `currentText()` / `QLineEdit.text()` 必须把原文还给
   程序内部，否则分析、面型编辑、优化变量会静默失效。详见
   [项目介绍](https://github.com/Kino2315/optiland-zh/blob/main/docs/intro.md)
   里「最难的部分：文字就是逻辑键」一节。
2. **`itemText()` 故意不打补丁。** Qt 用它渲染下拉列表。要动它之前先想清楚
   列表显示怎么办。

### 加一个拦截点

界面上还有英文，先判断它是怎么产生的：

```sh
python -m optiland_zh.audit          # 走一遍真实控件树，列出没翻的文字
```

如果 `audit` 报了「命中英文键，补丁没生效」，说明词库里有译文但补丁没拦到。
这时去 `engine.py` 看：

- 控件**构造时**传的文字 → 加进 `_CONSTRUCTORS`
- 控件**建立后**设的文字 → 加进 `_TEXT_METHODS`
- 参数是字符串列表 → 加进 `_LIST_METHODS`
- 静态对话框（`QMessageBox.information` 等）→ 加进 `_DIALOG_STATICS`
- 下拉框、输入框这种需要回译的 → 单独写包装器

**判断某个类该不该进 `_CONSTRUCTORS`**：看它的 `__init__` 有没有"一上来就是
标题"的位置参数。只收 `parent` 的（`QWidget` / `QMainWindow` / `QDialog` /
`QTabWidget`）不要加。

加完必须：

```sh
optiland-zh --self-test
python -m optiland_zh.audit
```

### 别忘了改提取器

新增了一个界面文字接口，`extract.py` 里的 `TEXT_APIS` 通常也要跟着加，
否则提取器捞不到通过它传的字符串，下次升级算差集就会漏。

反过来说：**往 `TEXT_APIS` 里加之前先确认那个接口收的全是给人看的文字。**
`_create_dock` 就是个反例——它第二个参数是 objectName，加了会把内部标识符
当成待翻译项收进来。

## 提交

- 一个小 PR 只做一件事：要么补词条，要么加语言，要么改引擎。
- 改引擎的 PR 请在描述里贴这两条命令的输出：
  `optiland-zh --self-test` 和 `python -m optiland_zh.audit`。
- 加语言的 PR 请贴 `optiland-zh -l <语言代码> --coverage` 的数字，别低得离谱
  （目前 zh_CN 是 99.5%）。

## 发布（维护者）

发布走 GitHub Actions。**不需要在本地跑 `twine upload`，也不需要持有 PyPI token**
——用的是 Trusted Publishing（OIDC），GitHub 拿一次性身份令牌去换上传权限。

### 步骤

**1. 改版本号，三处必须一致**（有测试守着，不一致 CI 就红）：

```
pyproject.toml                        version = "0.1.1"
src/optiland_zh/__init__.py           __version__ = "0.1.1"
src/optiland_zh/catalogs/zh_CN.json   "version": "0.1.1"
```

词库那个字段最容易漏 —— 它平时没人读。漏了测试会报
「zh_CN.json 里写的是 …，但包版本是 …」。

**2. 提交并推送**：

```sh
git add -A && git commit -m "release: v0.1.1" && git push
```

**3. 从命令行建 tag 并推送**：

```sh
git tag v0.1.1 && git push origin v0.1.1
```

> 推 tag 本身**不会触发任何东西**（workflow 只监听 `release: published`），
> 是安全的。
>
> 而且从命令行建 tag 能绕开一个很常见的坑：**在网页上手动输入 tag 时，
> 中文输入法会把 `v` 或 `.` 打成全角**（`ｖ0.1.1`），GitHub 会报
> `tag name is not well-formed`。命令行不会出这个问题。

**4. 去 Releases → Create a new release**，在 **Choose a tag** 的
**下拉列表里点选**刚推上去的 tag（**别手打**），标题和描述随意，
然后点 **Publish release**。

**5. 剩下的自动跑**：装依赖 → 跑测试 → 校验 tag 与 pyproject 版本一致 →
校验包内 `__version__` 一致 → 打包 → `twine check` →
校验项目描述能渲染 → 校验词库在 wheel 里 → OIDC 换令牌 → 上传 PyPI。

### 四个必须知道的点

- **版本号不能重传。** 同一个版本号发到 PyPI 之后不能再发第二次，哪怕内容是坏的。
  发现问题只能升版本号重发。

- **`twine check` 查不出 Markdown 的问题。** 它对 `text/markdown` 直接把渲染器
  设成 `None`（源码里注释写着 "Rendering cannot fail"），也就是**根本不做渲染**，
  却会报 PASSED。真正管这件事的是 `scripts/check_description.py`，
  CI 和发布流水线都会跑它。

- **README 里不能用相对路径。** PyPI 不解析相对路径：图片会变成破图、
  链接会 404，而渲染本身不会报错，所以只能靠上面那两个检查拦。

- **想先试水**，可以在 Actions 里手动跑 **Release** 工作流、target 选 `testpypi`。
  但那需要**单独注册一个 TestPyPI 账号**（独立账号体系）并再配一份
  pending publisher，成本不低。常规发版直接走正式 PyPI 即可。

### 首次配置（只做一次）

PyPI → Account settings → [Publishing](https://pypi.org/manage/account/publishing/)
→ Add a new pending publisher：

| 字段 | 值 |
|---|---|
| PyPI Project Name | `optiland-gui-zh` |
| Owner | `Kino2315` |
| Repository name | `optiland-zh` |
| Workflow name | `release.yml`（**文件名，不是 workflow 的显示名 `Release`**） |
| Environment name | `pypi` |

## 报告问题

带上这些信息，排查会快很多：

```sh
optiland-zh --list-languages
python -c "import PySide6, optiland; print(PySide6.__version__, optiland.__version__)"
```

以及出问题的那块界面的截图。
