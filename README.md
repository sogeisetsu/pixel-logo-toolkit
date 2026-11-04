# pixellogo

**English** | [简体中文](README.zh-CN.md)

[![tests](https://github.com/sogeisetsu/pixel-logo-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/sogeisetsu/pixel-logo-toolkit/actions/workflows/tests.yml)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

Render a title, a few subtitle lines and a footnote into **8-bit / retro-terminal pixel art**.
One command per image, PNG and SVG output, five canvases, ten palettes, and mixed
Latin / Chinese / Japanese / Korean text without missing glyphs.

![pixellogo sample output](docs/images/banner.png)

---

## Table of contents

- [Features](#features)
- [Install](#install)
- [Quick start](#quick-start)
- [Usage](#usage)
  - [Command structure and precedence](#command-structure-and-precedence)
  - [Recipes](#recipes)
  - [Canvas modes](#canvas-modes)
  - [Output formats and path rules](#output-formats-and-path-rules)
  - [Content fields](#content-fields)
  - [Style presets and colors](#style-presets-and-colors)
  - [Layout controls](#layout-controls)
  - [Background patterns](#background-patterns)
  - [Fonts and glyph variants](#fonts-and-glyph-variants)
  - [Interface language](#interface-language)
  - [Config files (JSONC)](#config-files-jsonc)
  - [Python API](#python-api)
  - [Flags and exit codes](#flags-and-exit-codes)
- [Preset gallery](#preset-gallery)
- [Command gallery](docs/gallery.md) — 52 rendered samples with the exact commands
- [Browsable gallery](docs/gallery.html) — the same set as a filterable, lazy-loaded page with a lightbox
- [Documentation](#documentation)
- [Development and tests](#development-and-tests)
- [FAQ](#faq)
- [License](#license)

---

## Features

- **Real pixels, not a filter**: text is rasterized into a binary mask, then merged per row
  into integer-coordinate rectangles. Every edge stays a whole block at any zoom — no
  anti-aliasing, no gradients, no feathering.
- **One geometry, two formats**: PNG and SVG come from the same `Scene`, so they match
  pixel for pixel. The SVG is fully self-contained and does not depend on font files.
- **Five canvases**: portrait poster, landscape card, repository banner, widescreen slide,
  square image — each with its own layout strategy.
- **Ten palettes**: from retro terminal to paper journal, each verified by a contrast check.
- **CJK-ready**: a Chinese pixel font ships in the box, so mixed Latin/Chinese lines keep one
  consistent stroke weight; Traditional Chinese, Japanese and Korean download on demand.
- **Reusable configuration**: JSONC config files (comments and trailing commas allowed) plus
  dot-path overrides, so one config can drive a whole batch.
- **No browser dependency**: pure Python and Pillow rasterization; runs on servers and in CI.
- **Bilingual CLI**: help page, option tables, `fonts` status, warnings and errors in English or
  Simplified Chinese — following the terminal locale or an explicit `--ui-lang`.

---

## Install

Requires Python ≥ 3.9. The only runtime dependency is Pillow.

```bash
# Recommended: isolated install with pipx, gives you the pixellogo command
pipx install git+https://github.com/sogeisetsu/pixel-logo-toolkit.git
```

```bash
# Or with pip
pip install git+https://github.com/sogeisetsu/pixel-logo-toolkit.git

# Or from source
git clone https://github.com/sogeisetsu/pixel-logo-toolkit.git
cd pixel-logo-toolkit
pip install .
```

> Cloning the repository alone does **not** create the `pixellogo` command; run one of the
> installs above. To skip installation entirely, run it from the repository with
> `PYTHONPATH=src python -m pixellogo ...`.

Verify the install:

```console
$ pixellogo --version
pixellogo 0.3.0

$ pixellogo --list modes
poster     3:4  Portrait poster (Xiaohongshu cover)        output 1080×1440
card       4:3  Landscape card (article header / slides)   output 1440×1080
banner     2:1  Repository banner (GitHub preview)         output 1280×640
slide     16:9  Widescreen slide (16:9)                    output 1920×1080
square     1:1  Square image (social avatar / grid)        output 1080×1080
```

Your terminal language decides the output language; `--ui-lang zh` switches to Chinese.
See [Interface language](#interface-language).

---

## Quick start

```bash
pixellogo -t "REA" -s "REVERSE ENGINEER" -d "One CLI for agents"
```

```console
$ ls out/
REA-poster.png  REA-poster.svg
```

Running `pixellogo` with no arguments prints the help page; `pixellogo --help`,
`pixellogo -h` and `pixellogo help` are equivalent.

More scenarios — different languages, canvases and textures, 52 rendered samples with their
commands — live in the [command gallery](docs/gallery.md) (currently in Chinese). To browse them
as a page instead, open the **[browsable gallery](docs/gallery.html)**.

---

## Usage

### Command structure and precedence

```
pixellogo [content] [style] [layout] [output] [-c CONFIG] [--set OVERRIDE]
```

Arguments take effect in four layers, each overriding the previous one:

```
built-in defaults  <  --preset  <  config file  <  command line (including --set)
```

Add `--dry-run` to inspect the merged result: it prints the final configuration without
rendering or writing anything.

```bash
pixellogo -c examples/og.jsonc -m slide --set colors.accent=#FF3D81 --dry-run
```

### Recipes

**1. Change the canvas**

```bash
pixellogo -t "PIXEL" -m slide           # 1920×1080
pixellogo -t "PIXEL" -m square          # 1080×1080
pixellogo -t "PIXEL" --size 1200x900    # any size, overrides -m
```

**2. Change the palette**

```bash
pixellogo -t "PIXEL" -p cyber           # neon cyber
pixellogo -t "PIXEL" -p paper           # paper journal
pixellogo --list presets                # see all ten
```

**3. Change a single color**

```bash
pixellogo -t "PIXEL" -p forest --accent "#FF3D81"
pixellogo -t "PIXEL" --bg "#0B1020" --fg "#E6EDF3" --primary "#7C3AED"
```

**4. Raster only, or vector only**

```bash
pixellogo -t "PIXEL" -f png -o out/     # PNG only
pixellogo -t "PIXEL" -f svg -o out/     # SVG only
pixellogo -t "PIXEL" -f both -o out/    # both (default)
```

**5. Pick the filename**

```bash
pixellogo -t "PIXEL" -o cover.png                    # writes cover.png
pixellogo -t "PIXEL" -f both -o cover.png            # writes cover.png + cover.svg
pixellogo -t "PIXEL" -o assets/covers/banner.png     # missing directories are created
```

**6. Chinese or Japanese titles**

```bash
pixellogo -t "像素工具包" -s "PIXEL LOGO TOOLKIT" --badge NEW
pixellogo -t "ピクセル" --lang ja        # requires pixellogo fonts install ja first
```

**7. Batch rendering from a config**

```bash
pixellogo -c examples/batch.jsonc -o out/ -f png
pixellogo -c examples/batch.jsonc -o out/ --json   # machine-readable result
```

**8. Add a texture and a motif**

```bash
pixellogo -t "PIXEL" --bg-pattern grid      # graph paper
pixellogo -t "PIXEL" --bg-pattern scanlines # CRT scanlines
pixellogo -t "PIXEL" -m banner --motif none # drop the bottom-right stair motif
```

**9. Open the result**

```bash
pixellogo -t "PIXEL" --open
```

### Canvas modes

Mode names are semantic words; the aspect ratio is a consequence, not the name. Legacy ratio
keys (`xhs`, `og`, `4:3`, `16:9`, `1:1` …) remain as aliases, so existing configs keep working.

| Mode | Output size | Ratio | Typical use | Layout character |
| --- | --- | --- | --- | --- |
| `poster` | 1080×1440 | 3:4 | Xiaohongshu covers, portrait posters | Centered, title fills the width |
| `card` | 1440×1080 | 4:3 | Article headers, slide artwork | Left-aligned, vertically centered |
| `banner` | 1280×640 | 2:1 | GitHub repository preview | Text on the left, stair motif bottom-right |
| `slide` | 1920×1080 | 16:9 | Slide covers | Left-aligned, generous whitespace |
| `square` | 1080×1080 | 1:1 | Social avatars, grid posts | Fully centered |

<table>
  <tr>
    <td align="center"><img src="docs/images/poster.png" width="200"><br><code>poster</code></td>
    <td align="center"><img src="docs/images/card.png" width="270"><br><code>card</code></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/square.png" width="200"><br><code>square</code></td>
    <td align="center"><img src="docs/images/slide.png" width="270"><br><code>slide</code></td>
  </tr>
</table>

Common aliases: `xhs` / `xiaohongshu` / `red` / `3:4` → `poster`; `og` / `github` / `repo` /
`social` / `2:1` → `banner`; `4:3` / `landscape` → `card`; `16:9` / `wide` → `slide`;
`1:1` / `avatar` → `square`.

Any mode can be overridden with `--size WIDTHxHEIGHT`; the output size is the logical size
multiplied by `--scale` (default 2).

### Output formats and path rules

| `-o` receives | `-f` | Result |
| --- | --- | --- |
| A directory (`out/`) | `png` | `out/<title>-<mode>.png` |
| A directory (`out/`) | `svg` | `out/<title>-<mode>.svg` |
| A directory (`out/`) | `both` | Both of the above |
| A file (`cover.png`) | `png` | `cover.png` |
| A file (`cover.png`) | `both` | `cover.png` + `cover.svg` |
| A file (`cover.png`) | `svg` | `cover.svg` (format comes from `-f`, stem is kept) |

- Spaces and illegal characters in the title become `-`; CJK characters are preserved.
- Batch runs never overwrite each other: duplicates get a suffix (`REA-poster-2.png`).
- `--scale` is an integer upscale factor, default 2; `--scale 1` matches the logical size.

### Content fields

| Flag | Meaning | Multi-line |
| --- | --- | --- |
| `-t, --title` | Main title, **required** | Separate with `\n`, or use `\n` in the config |
| `-s, --subtitle` | Subtitle line | Repeat the flag, one line each: `-s "A" -s "B"` |
| `-d, --desc` | Footer note line | Same as above: `-d "A" -d "B"` |
| `-e, --eyebrow` | Small label above the title | Single line |
| `--badge` | Badge text in the top-right corner | Single line |

```bash
pixellogo \
  -e "TOOLKIT / 2026" \
  -t "像素工具包" \
  -s "PIXEL LOGO TOOLKIT" -s "FOR AGENTS" \
  --badge NEW \
  -d "8-bit 风格图像生成器" -d "PNG / SVG 双格式输出"
```

### Style presets and colors

| Preset | Character | Background | Primary | Accent |
| --- | --- | --- | --- | --- |
| `terminal` | Retro terminal (default) | `#EEF1F6` | `#02ADFB` | `#FF6104` |
| `cyber` | Neon cyber | `#0D1117` | `#00E5A0` | `#FF3D81` |
| `arcade` | Retro arcade | `#1B1F27` | `#FFD200` | `#FF5F1F` |
| `candy` | Soft candy | `#FFF5F7` | `#FF7EB6` | `#4ECDC4` |
| `minimal` | Clean minimal | `#F8FAFC` | `#2563EB` | `#F97316` |
| `noir` | Monochrome documentary | `#F4F4F5` | `#18181B` | `#E11D48` |
| `forest` | Forest moss | `#F0F4EF` | `#2F6B3C` | `#D97706` |
| `sunset` | Dusk sunset | `#2B1B2F` | `#FF8A3D` | `#FFD166` |
| `ocean` | Deep ocean | `#E8F1F5` | `#0077B6` | `#2A9D8F` |
| `paper` | Paper journal | `#F5EEE1` | `#8C3B2E` | `#C9822E` |

`pixellogo --list presets` additionally reports the text-on-background contrast ratio of
each preset.

Single-color overrides (higher priority than the preset, each one independent):

```bash
--bg <HEX>  --fg <HEX>  --primary <HEX>  --accent <HEX>  --shadow-color <HEX>
```

A preset has six ingredients: background, text color, primary (title), accent (divider and
badge), shadow color, plus the font pairing and shadow strength.

### Layout controls

| Flag | Values | Default | Effect |
| --- | --- | --- | --- |
| `--align` | `auto` / `left` / `center` | `auto` | Horizontal alignment; `auto` follows the canvas |
| `--vertical` | `auto` / `top` / `center` | `auto` | Vertical anchoring of the content block |
| `--margin` | 0–0.4 | `0.06` | Safe margin, relative to the short edge |
| `--divider` | `line` / `dash` / `block` / `none` | from preset | Divider style between title and footnote |
| `--divider-width` | 0.05–1.0 | `0.42` | Divider width as a share of the text area |
| `--motif` | `auto` / `none` / `blocks` | `auto` | Pixel stair motif bottom-right (`banner` enables it) |
| `--title-size` | pixels | auto | Explicit title size; no upscaling |
| `--tracking` | 0.5–1.5 | `1.0` | Letter-spacing multiplier; `0.9` is tighter |
| `--leading` | 0.8–2.0 | `1.0` | Line-height multiplier |
| `--uppercase` | switch | off | Render all text in uppercase |
| `--wrap` / `--no-wrap` | switch pair | on | Wrap long subtitle/desc/eyebrow lines to the text area instead of clipping |
| `--shadow-offset` | 0–4 | `1` | Title shadow depth in blocks; `0` disables |

Title size auto-fits in both directions: long titles shrink to the text width, short titles
grow until they nearly fill it, capped at about 42% of the canvas height.

Subtitle, footnote and eyebrow lines **wrap automatically** to the text area; if the wrapped
block is still taller than the canvas, the font size steps down to 9px and only then reports a
warning. Pass `--no-wrap` to go back to single, overflowing lines.

```bash
pixellogo -t "PIXEL" --tracking 0.88 --leading 1.2 --uppercase
pixellogo -t "PIXEL" --align left --vertical top --divider dash
pixellogo -t "PIXEL" --shadow-offset 0            # flat, no shadow
pixellogo -t "PIXEL" -s "<a very long subtitle>" --no-wrap   # opt out of wrapping
```

### Background patterns

| Value | Effect | Notes |
| --- | --- | --- |
| `none` | Solid background | Default, keeps the "no texture" style invariant |
| `grid` | Graph paper | One cell per ~1/20 of the short edge, 1 px lines |
| `dots` | Dot matrix | Small blocks at grid intersections |
| `scanlines` | Scanlines | Evenly spaced horizontal lines, CRT look |

The texture color is a 10% mix of background and text color, so it stays a **solid** color —
no alpha, no gradients.

```bash
pixellogo -t "GRID" -p forest --bg-pattern grid
pixellogo -t "DOTS" -p paper --bg-pattern dots
pixellogo -t "SCANLINES" -p cyber --bg-pattern scanlines
```

<table>
  <tr>
    <td align="center"><img src="docs/images/pattern-grid.png" width="240"><br><code>--bg-pattern grid</code></td>
    <td align="center"><img src="docs/images/pattern-dots.png" width="240"><br><code>--bg-pattern dots</code></td>
    <td align="center"><img src="docs/images/pattern-scanlines.png" width="240"><br><code>--bg-pattern scanlines</code></td>
  </tr>
</table>

The three samples above use `forest`, `paper` and `cyber`: the texture follows the palette
instead of being a hard-coded gray.

### Fonts and glyph variants

Four fonts ship with the package, so no network access is needed after installation:

| Font | Role | Coverage |
| --- | --- | --- |
| Press Start 2P | Titles | Latin |
| Silkscreen | Subtitles | Latin (no lowercase glyphs) |
| Pixelify Sans | Body text | Latin (upper and lower case) |
| Ark Pixel 12px Proportional | Simplified / Traditional Chinese, Japanese fallback | Han, kana, Latin |
| Galmuri 11px | Korean fallback (download on demand) | Hangul, Han, kana, Latin |

With **mixed Latin and Chinese** text, the whole line switches to the Chinese pixel font
(so one line never mixes two stroke weights) and gains one extra step of weight.

**Glyph variants**: Simplified Chinese ships in the box; Traditional Chinese, Japanese and
Korean download on demand into `~/.pixellogo/fonts`.

```console
$ pixellogo fonts
zh-hans  bundled          Ark Pixel 12px (zh-hans)
zh-hant  downloaded       Ark Pixel 12px (zh-hant)
ja       downloaded       Ark Pixel 12px (ja)
ko       downloaded       Galmuri 11px (ko)

Font directory: C:\Users\you\.pixellogo\fonts
Install on demand: pixellogo fonts install <zh-hant|ja|ko>

$ pixellogo fonts install ja
Downloading the ja font pack (Ark Pixel 12px (ja))…
  https://github.com/TakWolf/ark-pixel-font/releases/download/2026.10.25/…
  100%  35MB / 35MB
Installed: C:\Users\you\.pixellogo\fonts\ArkPixel-ja.ttf

$ pixellogo -t "ピクセル" --lang ja
```

<table>
  <tr>
    <td align="center"><img src="docs/images/lang-ja.png" width="380"><br><code>--lang ja</code> renders kana and kanji with Japanese glyph shapes, one weight bolder</td>
  </tr>
</table>

- `--lang` accepts `zh-hans` / `zh-hant` / `ja` / `ko`, plus spellings such as `zh-cn`,
  `zh-tw`, `jp`, `kr`. It selects the **glyph variant**, not the interface language.
- Korean uses [Galmuri](https://github.com/quiple/galmuri) rather than Ark Pixel: the `ko`
  build of Ark Pixel contains no Hangul and would render a row of tofu boxes.
- Missing fonts are not an error when the content has no CJK characters at all.
- Environment variables: `PIXELLOGO_FONT_DIR` moves the font directory,
  `PIXELLOGO_FONT_MIRROR` points downloads at a mirror.
- Any pixel font works: `--font-title /path/to/font.ttf` (likewise `--font-sub`, `--font-body`).

### Interface language

All CLI text — help page, `--list` tables, `fonts` output, warnings and error messages — is
available in English and Simplified Chinese.

1. **Automatic.** The tool follows the terminal locale, checked in this order:
   `LC_ALL` → `LC_MESSAGES` → `LANG` → `LANGUAGE`; on Windows, when no locale variable is
   set, the system UI language is used. `C` / `POSIX` count as English, and anything that is
   not Chinese falls back to English.
2. **Explicit.** `--ui-lang auto|en|zh` overrides detection for one run, and the
   `PIXELLOGO_UI_LANG` environment variable sets a persistent default. The flag wins over the
   environment variable, which wins over the locale.

```bash
pixellogo --help                     # follows the terminal locale
pixellogo --ui-lang en --help        # force English
pixellogo --ui-lang zh --list modes  # Chinese list, regardless of locale

PIXELLOGO_UI_LANG=en pixellogo --list presets   # persistent choice via environment
```

> `--ui-lang` changes the wording of the CLI; `--lang` changes the glyph variant used to
> render the image. The two are independent: `--ui-lang en --lang ja` gives an English
> interface with Japanese glyphs.

### Config files (JSONC)

```jsonc
// examples/og.jsonc
{
  "mode": "banner",
  "preset": "cyber",

  "title": "像素工具包",
  "subtitle": "PIXEL LOGO TOOLKIT",     // string or array
  "desc": ["8-bit 风格图像生成器", "PNG / SVG 双格式输出"],

  "badge": "v0.1",
  "layout": {
    "divider": "line",
    "motif": "blocks",
  },
}
```

```bash
pixellogo -c examples/og.jsonc
pixellogo -c examples/og.jsonc -m card                    # command line overrides mode
pixellogo -c examples/og.jsonc --set colors.accent=#FF3D81
```

All available keys (identical to the `--dry-run` output structure):

| Key | Type | Meaning |
| --- | --- | --- |
| `mode` | string | Canvas mode, default `poster` |
| `size` | `"1200x900"` | Custom canvas, takes priority over `mode` |
| `preset` | string | Style preset, default `terminal` |
| `title` | string | Main title, required |
| `subtitle` / `desc` | string or array | One entry per line |
| `eyebrow` / `badge` | string | Small label / top-right badge |
| `lang` | string | Glyph variant, default `zh-hans` |
| `colors` | object | `bg` `fg` `primary` `accent` `shadow` |
| `fonts` | object | `title` `sub` `body` (font name or .ttf path) |
| `layout` | object | `align` `vertical` `margin` `divider` `dividerWidth` `titleSize` `shadowOffset` `motif` `pattern` `tracking` `leading` `uppercase` `cjkBold` |
| `output` | object | `dir` / `path` / `scale` / `formats` |
| `scale` / `out` / `format` | top-level shorthand | Equivalent to the matching key under `output` |

A top-level array means batch mode — one config, many images:

```jsonc
[
  { "mode": "poster", "title": "REA", "subtitle": ["REVERSE ENGINEER"] },
  { "mode": "banner", "title": "REA", "desc": ["Repository social preview"] }
]
```

```bash
pixellogo -c examples/batch.jsonc -o out/ -f png --json
```

Editor completion: add `"$schema"` pointing at
`src/pixellogo/schema/pixellogo.schema.json` (or the same file inside an installed package).

### Python API

```python
from pixellogo import render, render_many, make_image, make_scene, to_svg_text

# Write files, returns the generated paths
paths = render(title="REA", mode="banner", preset="cyber", format="png", out="out/")

# Pillow bitmap only (nothing written)
image = make_image(title="REA", mode="square", scale=1)
image.save("preview.png")

# Geometry only (inspect palette or bounds yourself)
scene = make_scene(title="REA", mode="poster")
print(scene.width, scene.height, len(scene.rects), scene.colors)

# SVG source only
svg = to_svg_text(title="REA", mode="slide")

# Batch
render_many(
    [{"title": "A", "mode": "poster"}, {"title": "B", "mode": "square"}],
    out="out",
    format="png",
)
```

Keyword names match the JSONC keys exactly, so anything valid in a config is valid here:

```python
render(
    title="像素工具包",
    subtitle=["PIXEL LOGO TOOLKIT"],
    colors={"primary": "#8C3B2E", "accent": "#C9822E"},
    layout={"align": "left", "divider": "dash", "pattern": "grid"},
    out="out/",
)
```

### Flags and exit codes

| Flag | Effect |
| --- | --- |
| `-h, --help` | Print help (bare `pixellogo` and `pixellogo help` do the same) |
| `-V, --version` | Print the version |
| `--ui-lang auto\|en\|zh` | Output language of the CLI itself |
| `--list modes` / `presets` / `fonts` | List the available options |
| `--dry-run` | Print the merged configuration, do not render |
| `--json` | Emit JSON results for scripting |
| `--open` | Open the first image with the system default application |
| `-c, --config` | JSONC config file |
| `--set KEY=VALUE` | Dot-path override, repeatable |

Exit codes: `0` success, `2` invalid arguments or configuration (error text goes to stderr).

---

## Preset gallery

<table>
  <tr>
    <td align="center"><img src="docs/images/preset-terminal.png" width="180"><br><code>terminal</code></td>
    <td align="center"><img src="docs/images/preset-cyber.png" width="180"><br><code>cyber</code></td>
    <td align="center"><img src="docs/images/preset-arcade.png" width="180"><br><code>arcade</code></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/preset-candy.png" width="180"><br><code>candy</code></td>
    <td align="center"><img src="docs/images/preset-minimal.png" width="180"><br><code>minimal</code></td>
    <td align="center"><img src="docs/images/preset-noir.png" width="180"><br><code>noir</code></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/preset-forest.png" width="180"><br><code>forest</code></td>
    <td align="center"><img src="docs/images/preset-sunset.png" width="180"><br><code>sunset</code></td>
    <td align="center"><img src="docs/images/preset-ocean.png" width="180"><br><code>ocean</code></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/preset-paper.png" width="180"><br><code>paper</code></td>
    <td></td>
    <td></td>
  </tr>
</table>

For the full set of combinations — canvases × presets × textures, plus localized Japanese /
Korean / Traditional Chinese examples — see the
**[command gallery →](docs/gallery.md)** (52 samples, each with its exact command;
currently written in Chinese). Prefer clicking through them? The
**[browsable gallery](docs/gallery.html)** renders the same set with category filters,
lazy loading and a keyboard-navigable lightbox.

---

## Documentation

Two in-depth guides live in `docs/` (currently written in Chinese):

- **[`docs/architecture.md`](docs/architecture.md)** — the project file tree (three levels, every entry annotated), the layer-by-layer module responsibilities, the render data flow, and the constraints this architecture imposes.
- **[`docs/cli-guide.md`](docs/cli-guide.md)** — the complete command-line manual: a guided quick start, every flag in detail, JSONC configs and batch mode, scripting and exit codes, plus a dedicated chapter on **limits and boundaries** (how many characters fit per canvas, line-count ceilings, which glyphs the bundled fonts are missing, which values the CLI cannot override) and a troubleshooting table.

---

## Development and tests

```bash
git clone https://github.com/sogeisetsu/pixel-logo-toolkit.git
cd pixel-logo-toolkit

PYTHONPATH=src python -m pixellogo --version
PYTHONPATH=src python -m unittest discover -s tests -v
```

```
src/pixellogo/
├─ cli.py        Command line entry point and argument parsing
├─ api.py        Python API
├─ config.py     Four-layer config merge and validation
├─ i18n.py       Bilingual CLI text, locale detection
├─ jsonc.py      JSONC parsing (comments / trailing commas)
├─ text.py       Text → mask → rectangles
├─ layout.py     Line stack layout, shadow, motif and background patterns
├─ modes.py      Canvas specifications
├─ presets.py    Style presets and contrast math
├─ fonts.py      Font registry, glyph coverage checks, language variants
├─ fontpack.py   On-demand multilingual font packs
├─ paths.py      Output naming rules
├─ scene.py      Primitive model
└─ render/       SVG and PNG backends
```

Style invariants are listed in [`docs/style-spec.md`](docs/style-spec.md); design and
implementation notes are in [`docs/design.md`](docs/design.md) (both in Chinese).

---

## FAQ

**The title came out too small.**
Title width is limited by the canvas mode and the text-area ratio. Use a wider canvas
(`-m slide`), reduce `--margin`, or set the size explicitly with `--title-size`.

**`pixellogo: command not found`.**
The package is not installed — cloning the repository is not enough. Run `pip install .`
(or `pip install -e .` for development, `pipx install .`) in the repository, then reopen the
terminal. If it still fails, check that Python's script directory is on `PATH`: on Windows
that is `<python>\Scripts`, on macOS / Linux usually `~/.local/bin`. To skip installation:
`PYTHONPATH=src python -m pixellogo -t "REA"`.

**Chinese characters render as boxes or are missing.**
Simplified Chinese ships by default. For Traditional Chinese, Japanese or Korean run
`pixellogo fonts install <lang>` and pass `--lang` accordingly.

**Will PNG edges have gray fringes?**
No. Rendering fills integer rectangles only and never resamples with interpolation.

**Can the background be an image?**
No — the style invariants require a solid background. Use `--bg-pattern` for graph paper,
dots or scanlines instead.

**How do I set the GitHub social preview?**
Generate a `banner` image (1280×640) and upload it under Settings → Social preview.

---

## License

Code is released under the [MIT license](LICENSE).
Bundled fonts follow the SIL Open Font License 1.1; the original texts live in
[`src/pixellogo/assets/licenses/`](src/pixellogo/assets/licenses/).
