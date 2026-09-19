# optiland-zh

**Simplified Chinese localization for the Optiland GUI** — a runtime
translation layer that patches nothing on disk.

English | [中文](https://github.com/Kino2315/optiland-zh/blob/main/README.md) | [PyPI](https://pypi.org/project/optiland-gui-zh/)

![screenshot](https://raw.githubusercontent.com/Kino2315/optiland-zh/main/docs/screenshot-zh.png)

> This README is the **reference manual**: install, usage, internals.
> For the **story and the technical highlights** — the "text is a logic key"
> trap, six traps found only by measurement, and how to audit a coverage
> number — see the [project introduction](https://github.com/Kino2315/optiland-zh/blob/main/docs/intro.md) (Chinese).

## What this is

[Optiland](https://github.com/optiland/optiland) is a full-featured open-source
optical design package (sequential/non-sequential ray tracing, optimization,
tolerancing, MTF, Zemax import, …) with a Qt GUI. The GUI is **English only** and
has no language switch: `self.tr()` appears zero times, there are no `.qm`/`.ts`
files, and it actively pins the locale:

```python
QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
```

This package makes the interface Chinese. It does **not** touch `site-packages`,
so `pip install -U optiland` leaves the localization intact.

## Install

Three audiences, three paths. **Almost everyone only needs the first one.**

### 1. Regular users

```sh
pip install "optiland[gui]"      # 1. Optiland itself (~300 MB)
pip install optiland-gui-zh      # 2. this localization layer (46 KB)
```

**Both lines are required.** This package deliberately does *not* declare
`optiland` as a dependency — doing so would drag in a full Qt/VTK stack and
fight with whatever version you already have installed. So pip will not pull it
in for you.

Then just run:

```sh
optiland-zh
```

One command. It installs the patches and launches the Optiland GUI.

> **No git involved anywhere in this path.** Users never clone the repository
> and never download Optiland's source — this package contains **none** of the
> upstream source; it patches Qt at runtime inside your own process.
> See [why](#the-hard-part-round-tripping).

### 2. From source

To read the code, to modify it, or while it isn't on PyPI yet:

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
pip install -e ".[dev]"     # -e = editable: edits take effect immediately
pytest -q
```

### Installed the localization layer but not the upstream?

You get this instead of a raw traceback:

```
[optiland-zh] 找不到：PySide6、optiland_gui

本包只是汉化层，**不含 Optiland 本体**。请先装上游：

    pip install "optiland[gui]"
```

Follow it and you're done. `--list-languages` and `--help` need no Qt at all
and work in any environment.

## Use

```sh
optiland-zh
```

That installs the patches and launches the GUI.

```sh
optiland-zh --list-languages
optiland-zh --coverage          # catalog coverage report
optiland-zh --self-test         # headless assertions
optiland-zh -c my.json          # custom catalog, for debugging
optiland-zh --no-locale         # translate text only, keep Qt locale
```

Or programmatically:

```python
import optiland_zh
optiland_zh.install()           # must run BEFORE QApplication is created
from optiland_gui.run_gui import main
main()
```

## The hard part: round-tripping

Localizing a Qt app naively breaks it. Optiland's GUI uses widget text as a
**logic key** in 18 places:

```python
self.on_analysis_type_changed(self.analysisTypeCombo.currentText())
```

That line looks up the analysis class registry by the text shown in the combo.
Translate `"Spot Diagram"` to `"点列图"` and `currentText()` returns Chinese,
the lookup misses, and **the entire analysis feature silently stops working**.

`QLineEdit` is worse — the surface-type editor reads back through it:

```python
new_type = self.type_edit.text()                            # lens_editor.py:205
if new_type.lower().strip() in get_available_surface_types():
```

The check runs against an **English** table. Translate one way only and
`"标准" in ["standard", ...]` is `False`, so editing a surface type silently fails.

So the engine is bidirectional:

| Direction | Mechanism |
|---|---|
| Text **into** Qt | EN→ZH (constructors, `setText`, `addItem`, `addMenu`, …) |
| Original **stored** | combo items: `userData` under a private role; line edits: a Qt dynamic property |
| Logic **reads back** | `currentText()` / `QLineEdit.text()` return the English |
| Lookup **by text** | `findText()` / `setCurrentText()` translate the query first |

The UI is Chinese; the application still sees English internally.

> `itemText()` is **deliberately not** round-tripped — Qt uses it to render the
> dropdown, so reversing it would show English in the list. The whole codebase
> calls it once, feeding `setCurrentText`, which already works.

## Non-obvious interception points

Patching `QLabel` alone is not enough. Each of these was found by measurement:

| Trap | Why it breaks | Fix |
|---|---|---|
| `QFormLayout.addRow("label", widget)` | The QLabel is built inside Qt's **C++** side | patch `addRow` (19 labels were missed) |
| `QDockWidget("title", parent)` | Not in the constructor whitelist | add it |
| Qt's own OK / Cancel / Open / Save | Those strings are not in Optiland's source at all | load `qtbase_zh_CN.qm` (ships with PySide6) |
| Optimizer items padded with leading spaces | `" Least Squares"` never matches `"Least Squares"` | whitespace-tolerant lookup, indentation preserved |
| Templates like `Toggle {0}` | The captured `"Analysis"` is not translated, yielding 「显示/隐藏 Analysis」 | captured groups are re-looked-up in the static entries |

## Catalogs

Catalogs are plain data, one JSON per language, in `src/optiland_zh/catalogs/`.

```json
{
  "language": "zh_CN",
  "entries": { "&File": "文件(&F)" },
  "patterns": [
    { "match": "Field {0}: ({1}, {2})", "replace": "视场 {0}：({1}, {2})" }
  ]
}
```

`patterns` use positional placeholders and are compiled to regex at runtime —
far friendlier than asking translators to write `(?P<n>.+?)`.

### Adding entries or a language

1. Copy `src/optiland_zh/catalogs/zh_CN.json`
2. Change `language` / `display_name`
3. Translate `entries` and the `replace` side of `patterns` (**never `match`**)
4. Run `optiland-zh -l <lang> --coverage`

## After upgrading Optiland

Use the extractor to compute the gap:

```sh
python -m optiland_zh.extract --diff src/optiland_zh/catalogs/zh_CN.json
```

It walks the source AST and reports untranslated strings grouped by file. The
extractor is **context aware** and filters out:

- `setObjectName("AnalysisPanel")`-style internal identifiers
- docstrings
- `print()` / `logger.debug()` output
- stylesheets, shortcuts (`Ctrl+Q`), config keys (`Layouts/Config`)
- embedded code snippets

Without that filtering the first run yields 857 candidates, mostly noise;
proper filtering reduces it to 312, all of them genuinely translatable.

## Verification

```sh
optiland-zh --self-test        # 7 assertions incl. round-trip and findText
optiland-zh --coverage         # static coverage against the source
python -m optiland_zh.audit    # builds the real window offscreen and checks it
```

`--audit` is the strongest evidence: it instantiates every panel (including
collapsed menus and inactive tabs) and compares each text node against the
catalog.

```
text nodes in the window tree: 1082
  covered: 1047  (96.8%)
  missing: 35

classification, strongest rule first:
    974  exact-value           text equals a catalog translation exactly
     73  cjk-heuristic         contains Chinese (loose rule)
     35  MISS:not-translatable a number / objectName / third-party identifier

strict accounting (exact-value only): 974 / 1082 = 90.0%
real gaps (patch did not fire + still English): 0
```

**Why the breakdown matters.** "96.8% covered" alone does not say how much of
it rests on the loose rule. `exact-value` is hard evidence; `cjk-heuristic`
covers strings assembled by dynamic rules, which never appear verbatim in the
catalog but are plainly Chinese. Audit them individually:

```sh
python -m optiland_zh.audit --rule cjk-heuristic
```

All 73 check out: Qt-derived tooltips (`文件(&F)` → `文件(F)`), dynamic messages
(`显示/隐藏 分析`, `视场 1：(0.000, 0.000)`), and indented combo items.

The number that actually matters is **`real gaps = 0`**: nowhere does a catalog
translation exist without being applied, and nowhere does translatable English
remain. The other 35 are **correctly English**: Qt object names
(`QuickActionsToolbar`), scipy algorithm names (`BFGS`, `SLSQP`,
`trust-constr`), slot numbers, the brand `Optiland`, and `|||`.

> Do not conflate the two percentages. `--coverage` is **99.5%** — how many
> strings *in the source* are translated. `--audit` is **96.8%** — how much of
> the text *actually on screen* is Chinese. The first counts source literals,
> the second counts runtime widgets; one literal can appear on dozens of
> widgets, while dynamically assembled strings appear in no source literal at
> all, so the two numbers will never match.

> `--audit` disables VTK: on the offscreen platform there is no OpenGL pixel
> format and the 3D view segfaults the process (0xC0000005 on Windows).
> The GUI then takes its "VTK is not available" fallback and all text is intact.

## Known limitations

- **Text drawn into figures is out of reach.** Plot titles such as
  `System: Default System (2D)` are rendered by matplotlib, not by Qt widgets,
  so this patch layer cannot reach them. Would need matplotlib's own i18n.
- **Optiland's UI only.** Text from third-party widgets (Jupyter console menus,
  …) is covered incidentally by the generic Qt patches; the rest depends on
  those projects' own translations.
- **PySide6 version differences.** A few classes move between modules
  (`QStandardItem` lives in `QtGui`, not `QtWidgets`). The engine skips classes
  it cannot resolve instead of crashing; the affected widgets stay English.

## Terminology

Aligned with Zemax's Chinese edition:

| English | Chinese |
|---|---|
| Lens Data Editor | 镜头数据编辑器 |
| Aperture / Field / Wavelength | 孔径 / 视场 / 波长 |
| Radius / Thickness / Material / Conic | 半径 / 厚度 / 材料 / 圆锥系数 |
| Stop / Sag / Semi-Diameter | 光阑 / 矢高 / 半口径 |
| Spot Diagram / Ray Fan | 点列图 / 光线扇形图 |
| OPD / MTF / PSF | 光程差 / 调制传递函数 / 点扩散函数 |

**Deliberately untranslated**: `Cascadia Code` (a font name — translating it
would change the font), scipy algorithm names, Qt object names.

## License

MIT — see [LICENSE](https://github.com/Kino2315/optiland-zh/blob/main/LICENSE).

Upstream [Optiland](https://github.com/optiland/optiland) is MIT as well
(Copyright © 2024 Kramer Harrison). This project works by runtime patching and
neither redistributes nor modifies its source. Third-party components and
terminology sources are documented in [NOTICE.md](https://github.com/Kino2315/optiland-zh/blob/main/NOTICE.md).

## Contributing

See [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md). The most valuable contributions are
**new languages** and **new entries** — neither requires knowing Python.
