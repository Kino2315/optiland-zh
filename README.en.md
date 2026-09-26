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

```sh
optiland-zh                    # launch (from a terminal; shows diagnostics)
optiland-zh-gui                # launch (for double-clicking; no console window)
optiland-zh --list-languages   # list available languages
optiland-zh --self-test        # headless self-check, no window
optiland-zh --coverage         # catalog coverage report
```

Or drive it from your own script:

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
| **Change the engine** | When English remains, run `optiland-zh --audit` to find which interception point it belongs to, then follow the "changing the engine" section of [CONTRIBUTING.md](https://github.com/Kino2315/optiland-zh/blob/main/CONTRIBUTING.md) |

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
