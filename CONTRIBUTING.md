# 贡献指南

三条路，按所需技能从低到高。

## 一、补词条（不需要懂 Python）

1. 跑一遍提取器看还缺什么：

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

**术语请对齐 Zemax 中文版**，见 README 底部的对照表。新术语先查一下
《光学名词》或 Zemax 中文界面，不要自己造词。

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
   程序内部，否则分析、面型编辑、优化变量会静默失效。详见 README 的
   「最难的部分」。
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
- 改引擎的 PR 请在描述里贴 `--self-test` 和 `--audit` 的输出。
- 加语言的 PR 请贴 `--coverage` 的数字，别低得离谱（目前 zh_CN 是 99.5%）。

## 报告问题

带上这些信息，排查会快很多：

```sh
optiland-zh --list-languages
python -c "import PySide6, optiland; print(PySide6.__version__, optiland.__version__)"
```

以及出问题的那块界面的截图。
