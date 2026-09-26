# optiland-zh

> vibe coding

**It turns the Optiland interface into Chinese.** It does not modify Optiland's
code — at startup it swaps the English on screen for Chinese. So Optiland itself
has to be installed separately (see "Installation" below).

English | [中文](https://github.com/Kino2315/optiland-zh/blob/main/README.md)

![screenshot](https://raw.githubusercontent.com/Kino2315/optiland-zh/main/docs/screenshot-zh.png)

> This package localizes a Chinese-facing application, so **the tools' own console
> output is in Chinese.** Sample output below is reproduced verbatim.
>
> For the **story behind the project and the technical points worth reading** (text
> doubles as a logic key, six traps found the hard way, how to review a coverage
> number), read the [project introduction](https://github.com/Kino2315/optiland-zh/blob/main/docs/intro.md) (Chinese).

## What this is

[Optiland](https://github.com/optiland/optiland) (hereafter **upstream**) is a
complete open-source optical design package (sequential/non-sequential ray
tracing, optimization, tolerancing, MTF, Zemax file import …) with a Qt GUI. But
it is **English only, and has no language switch at all**.

This package **does not modify upstream's code**. At startup it replaces the
interface text. Therefore:

- **`pip install -U optiland` will not wipe the localization.** The localization
  does not live in upstream's files, so upgrading cannot touch it.
- **But an upgrade can still break it.** Replacement works by "remembering what
  every widget in upstream is called". If upstream renames one, that spot silently
  reverts to English — **with no error at all**. After upgrading, run
  [`optiland-zh --self-test`](#checking-whether-the-localization-broke) to find out.

## Installation

### 1. Regular users

```sh
pip install "optiland[gui]"      # (1) Optiland itself (~440 MB download)
pip install optiland-gui-zh      # (2) this localization package (50 KB)
```

**Both lines are required.** This package deliberately does not declare an
`optiland` dependency — doing so would force a full Qt and VTK stack on you and
fight with the version you already have installed.

You get two launch commands, for different purposes:

| Command | Console window | Use it for |
|---|---|---|
| `optiland-zh` | yes | Working from a terminal. Diagnostics appear outside the window when something fails |
| `optiland-zh-gui` | no | Double-clicking. No black console box; errors appear in a dialog |

### Desktop icon

```sh
optiland-zh --install-shortcut
```

creates an **Optiland 中文版** shortcut on your desktop; double-click it to start
with the Chinese interface. By default it points at the **console-less** entry
point (that is, `optiland-zh-gui`).

| What you want | Command |
|---|---|
| Create it in another directory | `optiland-zh --install-shortcut --shortcut-dir <directory>` |
| Keep a console so you can read errors | `optiland-zh --install-shortcut --console-shortcut` |
| Remove it | `optiland-zh --uninstall-shortcut` |

`--uninstall-shortcut` **only deletes the one name this tool created itself**; it
will not touch shortcuts you made by hand.

> The icon file is generated in `%LOCALAPPDATA%\optiland-zh\`.

### 2. From source

If you want to read the code or contribute:

```sh
pip install "optiland[gui]"
git clone https://github.com/Kino2315/optiland-zh
cd optiland-zh
pip install .
```

### 3. Development

```sh
git clone https://github.com/Kino2315/optiland-zh
cd optiland-zh
pip install -e ".[dev]"     # -e is editable: edits take effect at once, no reinstall
pytest -q
```

### Installed the localization but not upstream?

You will see this message:

```
[optiland-zh] 找不到：PySide6、optiland_gui

本包只是汉化层，不含 Optiland 本体。请先装上游：

    pip install "optiland[gui]"

（汉化包刻意不声明 optiland 依赖，免得和你已经装好的 Qt 版本打架。）
```

Just follow it. `--list-languages` and `--help` do not need Qt.

## Usage

```sh
optiland-zh
```

That one command installs the localization, then starts the Optiland GUI.

It takes options too:

```sh
optiland-zh --list-languages    # list the languages shipped with this package
optiland-zh -l zh_CN            # pick the interface language (-l is short for --language)
optiland-zh -c my.json          # use a catalog you wrote yourself (-c is short for --catalog)
optiland-zh --no-locale         # replace text only, leave Qt's locale alone
```

There are also three **inspection tools** (`--self-test` / `--coverage` /
`--audit`) that you will not need day to day — see
[checking whether the localization broke](#checking-whether-the-localization-broke).

To use it from your own script (`QApplication` is Qt's application object, and the
localization patch has to be installed before it exists):

```python
import optiland_zh

optiland_zh.install()  # must come before QApplication
from optiland_gui.run_gui import main
main()
```

> **Why not just edit the source?**
> Editing the files in `site-packages` is the easiest thing in the world, but a
> single `pip install -U optiland` wipes it all, and it cannot be distributed as a
> separate project. So the approach here is: **replace the text before it reaches
> Qt.** The patch is applied by assignment onto PySide6's binding types.

## Catalogs

Each language is one JSON file under `src/optiland_zh/catalogs/`. (Currently only
Simplified Chinese.)

Roughly like this — the real file also carries `display_name`, `version` and other
fields, so **when adding a language, copy an existing file** rather than writing
one from scratch:

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

Dynamic messages use `{0}` `{1}` placeholders (same syntax as Python's
`str.format`); the real values are filled in at runtime. At startup these
templates are compiled into match rules, which recognize text the interface has
"assembled" on the fly.

### Contributing: entries / languages

1. Copy `src/optiland_zh/catalogs/zh_CN.json`
2. Change `language` / `display_name`
3. Translate `entries` and the `replace` side of `patterns` (**never touch `match`**)
4. Run `optiland-zh -l <your language> --coverage` and look at the coverage.

See [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md) for details.

#### Added after an upgrade

After an Optiland upgrade the interface may contain new English — text from a new
feature that nobody has translated yet. **This is usually not a broken
localization, just an untranslated string** — but do not guess, check:

```sh
optiland-zh --lookup "the English text"
```

It ignores `&` and a trailing ellipsis, so **type it exactly as you see it on
screen.** (The screen may show `Save System` while the catalog key is
`&Save System`; you do not need to know that.)

- **Found** → the catalog has a translation, yet the screen is still English →
  **the patch did not intercept that widget** → the engine needs fixing, not the
  catalog.
- **Not found** → **nobody has translated it yet** → read on.

Adding entries is a **contributor** job (someone who cloned the repo). **Regular
users do not need to bother** — even if you edit the catalog inside
`site-packages`, the next `pip install -U optiland-gui-zh` (upgrading the
localization package) overwrites it. Confirming whether the *patch* stopped
working — which is what "broken" really means — is a different question: run
[`optiland-zh --self-test`](#checking-whether-the-localization-broke).

**Contributors: first see what is missing**

```sh
optiland-zh --extract --diff src/optiland_zh/catalogs/zh_CN.json
```

`--extract` scans the `optiland_gui` **installed in the current environment** and
picks out every string that "looks like interface text"; `--diff` then compares
those results against the catalog you passed and **lists only what is still
missing**, grouped by source file:

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

> **Those two totals do not measure the same thing:**
> `静态候选 312 + 动态模式 72 = 384` is **scanned out of the source code**;
> `已翻译 508` is **the size of the catalog itself** (436 entries + 72 dynamic rules).
> Different denominators — do not subtract one from the other.

**Three things about directories and paths that are easy to confuse:**

1. **Why "run it from the repository root"** — only because the
   `src/optiland_zh/catalogs/zh_CN.json` at the end of the command is a relative
   path written for the repository layout; from another directory that file is not
   found. Replace it with an absolute path and it runs from anywhere.
2. **`--diff` must point at the catalog in the repository** (the one you are about
   to edit), **not** the installed copy in `site-packages` — otherwise you are
   comparing "the old installed catalog" against "the installed interface", which
   says nothing about the entries you are about to change.
3. **What it scans is the `optiland_gui` installed in the current environment, not
   the code in the repository.** That part has nothing to do with your current
   directory.

**How it decides which strings should not be translated**

It uses Python's **AST (abstract syntax tree)**: `.py` files are first parsed into
syntax structure, and strings are then found in that structure instead of by
regex over raw text. So the following **never become candidates at all**:

- widget-internal names such as `setObjectName("AnalysisPanel")`
- docstrings
- console output such as `print()` / `logger.debug()`
- stylesheets (QSS), shortcuts (`Ctrl+Q`), config keys (`Layouts/Config`)
- example code snippets

**But there is a second gate, and that one needs human judgement.** The list above
only covers "never a candidate"; among the strings that *do* become candidates
there are still `Cascadia Code` (a font name) and `Optiland` (a brand name) that
**should not be translated in the first place**. They will sit in the
"untranslated" list forever — **that is normal, ignore them.**

When you are done, run `optiland-zh --coverage` and see whether the number went
up. If you installed via "3. Development" above with `pip install -e ".[dev]"`,
catalog edits take effect immediately with no reinstall; with a normal install,
run `pip install .` once more.

## Checking whether the localization broke

You will not need these three day to day. Reach for them **when English shows up
in the interface, or after upgrading Optiland.**

```sh
optiland-zh --self-test   # has anything I already translated stopped working?
optiland-zh --coverage    # is anything missing from the catalog?
optiland-zh --audit       # check every string the interface actually renders
```

**`--self-test` checks "has anything I already translated stopped working".**

The localization works by replacing interface text while the program runs. To be
precise, it remembers the name of every widget in Optiland and swaps the text for
Chinese before it reaches the screen. **If an Optiland upgrade renames a widget,
that replacement stops working — and reports no error** — and the interface
quietly reverts to English.

The command exercises 7 representative cases. When everything is fine it looks
like this:

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

If one case fails, that line becomes `[FAIL]`, and the last line tells you
`自检失败 1 项: …`.

**`--coverage` checks "is anything missing from the catalog".**

Every Optiland upgrade may add interface text. This command scans Optiland's
source, counts how many strings are translated and how many are not, and names the
missing ones:

```
词库: 简体中文 (zh_CN)
  静态界面文字 :  310 / 312   99.4%
  动态消息模板 :   72 / 72   100.0%
  合计         :  382 / 384   99.5%

未翻译的静态条目（前 30 条）:
    'Cascadia Code'
    'Optiland'
```

Those last two are a font name and a brand name; **they should not be translated
in the first place.**

**`--audit` checks "is there any English left on screen".**

The first two check the *catalog* and the *patch*. This one checks the text that is
**actually rendered**. It constructs Optiland's real main window in full (using
Qt's offscreen mode, so no window appears on screen), walks the entire widget tree,
and compares every string against the catalog — **including menus that were never
opened and tabs that were never clicked.** That is more reliable than eyeballing a
screenshot: a screenshot only shows the current screen.

When it finishes it prints:

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

**Which number to look at here:**

- **Look at whether "真缺口" (the real gap) is 0.** It counts "the catalog has a
  translation but the patch did not take effect" plus "still the original English"
  — **things that should have been translated and were not.** If it is 0, the
  localization is healthy.
- **The 35 "未覆盖" (uncovered) are not a problem.** They are widget-internal names
  like `QuickActionsToolbar`, scipy algorithm names like `BFGS`, ordinal numbers,
  decorations — **they should not be translated in the first place.**
- **Do not get tangled up in the two percentages.** 96.8% and 90.0% measure the
  same thing under different rules: the first also counts text that "obviously
  looks Chinese", the second only counts strings equal character-for-character to
  a catalog value. **Judge the localization by the "real gap"; do not agonize over
  either number.**

**Want to see exactly which nodes are in one bucket?**

```sh
optiland-zh --audit --rule cjk-mixed
```

It lists that bucket node by node, in the format "widget type / origin / text":

```
=== 判据 cjk-mixed 命中的节点（43 条去重）===
    ActionTip  QMenu      文件(F)
    ComboItem  QComboBox  通用 (scipy.minimize)
    ...
```

`--rule` accepts one of these 6 values:

```
exact-value              cjk-only                 cjk-mixed
MISS:patch-not-fired     MISS:still-translatable  MISS:not-translatable
```

A misspelled name errors out on the spot; it does not silently return 0 rows.

**The three percentages are not the same thing — do not mix them up:**

| Number | From | What it measures |
|---|---|---|
| **99.5%** | `--coverage` | of the strings extractable from upstream's source, how many are translated |
| **96.8%** | `--audit` "covered" | of the text actually rendered on screen, how much is already Chinese |
| **90.0%** | `--audit` "strict" | same, but counting only strings equal character-for-character to a catalog value |

They **should not be equal**: the first is computed over source files, the last two
over runtime widgets — one string can appear on dozens of widgets; conversely, text
assembled dynamically at runtime does not exist in the source at all.

**The two "untranslated" lists are not the same thing either:**

- `--coverage`'s "untranslated static entries" = strings that exist in the source
  but cannot be found in the catalog. **Some of them should not be translated**
  (a font name like `Cascadia Code`, for instance).
- `--audit`'s "未覆盖: 35" = of the text rendered on screen, the ones the catalog
  cannot resolve. **All 35 of them need no translation.**
- `--audit`'s "**真缺口**" (real gap) = things that should have been translated but
  were not. **This is the one that, at 0, means the localization is fine.**

## Known limitations

- **Text drawn inside plots cannot be translated.** Window titles such as
  `System: Default System (2D)` are drawn by matplotlib, not by a Qt widget, so this
  approach's patch cannot reach them. It would need matplotlib's own translation
  mechanism; not implemented yet.
- **Only Optiland's own interface is covered.** Third-party widgets (the Jupyter
  console's context menu, for instance) get whatever Qt's generic patch happens to
  cover; the rest depends on their own localization mechanisms.
- **PySide6 version differences.** A few classes live in different modules across
  versions (`QStandardItem` is in `QtGui`, not `QtWidgets`); the engine skips
  classes it cannot find, and the corresponding widgets stay untranslated.

## Terminology used when translating upstream

| English | Chinese |
|---|---|
| Lens Data Editor | 镜头数据编辑器 |
| Aperture / Field / Wavelength | 孔径 / 视场 / 波长 |
| Radius / Thickness / Material / Conic | 半径 / 厚度 / 材料 / 圆锥系数 |
| Stop / Sag / Semi-Diameter | 光阑 / 矢高 / 半口径 |
| Spot Diagram / Ray Fan | 点列图 / 光线扇形图 |
| OPD / MTF / PSF | 光程差 / 调制传递函数 / 点扩散函数 |

## License

MIT — see [LICENSE](https://github.com/Kino2315/optiland-zh/blob/main/LICENSE).

Upstream [Optiland](https://github.com/optiland/optiland) is MIT as well
(Copyright © 2024 Kramer Harrison). This project works by patching at runtime; it
neither distributes nor modifies upstream's source. Third-party components and the
sources of terminology are documented in
[NOTICE.md](https://github.com/Kino2315/optiland-zh/blob/main/NOTICE.md).

## Contributing

See [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md).
Both **new languages** and **additional entries** are welcome.
