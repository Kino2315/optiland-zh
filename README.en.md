# optiland-zh

**Simplified Chinese localization for the Optiland GUI.** A runtime translation
layer that patches Qt inside its own process. It is only a patch — you still
need Optiland itself installed.

![screenshot](https://raw.githubusercontent.com/Kino2315/optiland-zh/main/docs/screenshot-zh.png)

English | [中文](https://github.com/Kino2315/optiland-zh/blob/main/README.md) | [PyPI](https://pypi.org/project/optiland-gui-zh/)

## Quick start

```sh
pip install "optiland[gui]" optiland-gui-zh
optiland-zh
```

Both `pip` lines are required. This package deliberately does not declare
`optiland` as a dependency — doing so would drag in a full Qt/VTK stack and fight
with whatever version you already have installed, so pip will not pull it in.

## Usage

**Launch:**

```sh
optiland-zh       # from a terminal; errors are visible outside the window
optiland-zh-gui   # for double-clicking; no black console window
```

**Inspection tools** — they print a result and exit without opening the GUI:

```sh
optiland-zh --list-languages   # list the languages shipped with this package
optiland-zh --self-test        # is the translation patch actually taking effect?
optiland-zh --coverage         # how much interface text does the catalog cover?
optiland-zh --audit            # check every string the interface actually renders
```

You do not need these day to day. Reach for them **when English shows up in the
interface, or after upgrading Optiland.** Here is what each one covers:

**`--self-test` — has anything I translated stopped working?**

The localization works by replacing interface text while the program runs. It
remembers the name of every widget in Optiland and swaps the text before it
reaches the screen.

**If an Optiland upgrade renames a widget, that replacement silently stops
working — with no error message** — and the interface quietly reverts to English.
`--self-test` exercises seven representative cases and tells you which one failed:

```
[FAIL] 'Spot Diagram' -> 'Spot Diagram'    <- not replaced; still English
1 check failed: Spot Diagram
```

**`--coverage` — is anything missing from the catalog?**

Every Optiland upgrade may add new interface text. This command scans Optiland's
source, counts how many strings the catalog already covers and how many it does
not, and names the ones that are missing:

```
Catalog: Simplified Chinese (zh_CN)
  Static interface text :  310 / 312   99.4%
  Dynamic message templates :  72 / 72   100.0%
  Total                 :  382 / 384   99.5%

Untranslated static entries (first 30):
    'Cascadia Code'
    'Optiland'
```

Those last two are a font name and a brand name — they **must not** be translated.

**`--audit` — is there any English left on screen?**

The first two check the *catalog* and the *patch*. This one checks the text that
is **actually rendered**. It constructs Optiland's real main window, walks the
entire widget tree, and compares every string it finds against the catalog —
**including menus that were never opened and tabs that were never clicked.**

That is more reliable than eyeballing a screenshot: a screenshot only shows the
screen you are looking at.

> "Offscreen" is a Qt run mode: the interface is built as usual but never shown on
> a display. That is why this works from a terminal and on a headless server.

**Or drive it from your own script:**

```python
import optiland_zh

optiland_zh.install()                    # must run BEFORE QApplication exists
from optiland_gui.run_gui import main
main()
```

## Troubleshooting

**`PySide6` or `optiland_gui` not found**

You installed the localization layer but not Optiland itself. Run
`pip install "optiland[gui]"`.

**Want a desktop icon**

`optiland-zh --install-shortcut` creates it; `optiland-zh --uninstall-shortcut` removes it.

**Want another language, or want to add one**

Catalogs are plain JSON, and adding a language needs no Python. See
[CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md).

## What it does

Optiland ships a Qt GUI, but it is English-only with no language switch. This
package patches PySide6 bindings at runtime, replacing text before it reaches
Qt — so `pip install -U optiland` leaves the localization intact.

Two things are worth knowing:

**The UI is Chinese; the application still reads English internally.** The GUI
calls `currentText()` and uses that text as a logic key in 18 places — for
example, looking up the analysis-class registry by the name shown in a combo
box. Translating one way only would make those features **fail silently**. So
`currentText()` and `QLineEdit.text()` hand the original English back.

**Widgets Qt creates inside C++ are covered too.** That includes the labels made
by `QFormLayout.addRow` and the titles of `QDockWidget`s — constructions Python
never sees. Qt's own dialog buttons (OK / Cancel / Open) are handled by loading
`qtbase_zh_CN.qm`.

Full technical notes: [project introduction](https://github.com/Kino2315/optiland-zh/blob/main/docs/intro.md) (Chinese).

## Known limitations

- Text drawn into figures (matplotlib plot titles) is out of reach
- Only Optiland's own UI is covered; third-party widgets depend on their own i18n

## Contributing

Three ways to help, ordered by the skill required. **The first two need no Python.**

Run the commands below from the **repository root** (their paths are relative):

| Goal | How |
|---|---|
| **Add entries** | `optiland-zh --extract --diff src/optiland_zh/catalogs/zh_CN.json` lists what is missing; add translations to `entries` |
| **Add a language** | Copy `catalogs/zh_CN.json`, change `language` and `display_name`, translate the values of `entries` and the `replace` side of `patterns` (never `match`) |
| **Change the engine** | When English remains, run `optiland-zh --lookup "the English text"` first — if the catalog has it, the patch failed to intercept it (an engine problem); if not, nobody has translated it yet (an entry problem). Once you know it is the engine, use `optiland-zh --audit` to find which interception point it belongs to, then follow the "changing the engine" section of [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md) |

Before submitting:

```sh
pytest -q
optiland-zh --self-test
```

## License

MIT — see [LICENSE](https://github.com/Kino2315/optiland-zh/blob/main/LICENSE).
Upstream [Optiland](https://github.com/optiland/optiland) is MIT as well;
third-party components are documented in
[NOTICE.md](https://github.com/Kino2315/optiland-zh/blob/main/NOTICE.md).
