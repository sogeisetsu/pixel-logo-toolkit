# 命令行使用说明

本文是 `pixellogo` 的完整命令行手册，按「先会用、再会调、最后知道边界」的顺序组织：

- 第一次用 → 读第一、二、三节，十分钟内能出图；
- 日常查参数 → 读第四节速查表，需要细节再跳到第五、六节；
- 写脚本、接 CI → 读第七、八节，以及第九节的退出码与错误约定；
- 想知道「能放多少字、会不会缺字」→ 直接读第十节「能力边界与限制」。

文中的 CLI 输出片段统一用 `--ui-lang zh` 强制中文；实际运行时会跟随终端语言（见第七节）。

---

## 目录

- [一、这份文档怎么读](#一这份文档怎么读)
- [二、五分钟上手](#二五分钟上手)
- [三、心智模型：一条命令做了什么](#三心智模型一条命令做了什么)
- [四、参数速查](#四参数速查)
- [五、逐项详解](#五逐项详解)
- [六、配置文件（JSONC）](#六配置文件jsonc)
- [七、输出、路径与界面语言](#七输出路径与界面语言)
- [八、脚本化：JSON 结果、退出码与 Python API](#八脚本化json-结果退出码与-python-api)
- [九、能力边界与限制](#九能力边界与限制)
- [十、排错手册](#十排错手册)
- [附录](#附录)

---

## 一、这份文档怎么读

`pixellogo` 只有**一个命令**、**一个真子命令**（`fonts`），其余全是开关。所以先记住调用骨架，再按需查表：

```bash
pixellogo [内容] [风格] [排版] [输出] [-c 配置文件] [--set 覆盖] [--json|--open|--dry-run]
```

| 你的身份 / 目标 | 重点读 |
| --- | --- |
| 第一次用，想先出一张图 | 第二节、第五节的内容字段与画布 |
| 要批量出图（一套模板反复用） | 第六节 配置文件、第三节 优先级 |
| 写脚本、接 CI、要机器可读结果 | 第八节 JSON 结果与退出码 |
| 出图效果不对，来查原因 | 第十节 排错手册 |
| 想知道字数上限、字体缺字情况 | 第九节 能力边界与限制 |

---

## 二、五分钟上手

### 2.1 安装（三选一）

```bash
# 推荐：独立环境安装，直接获得 pixellogo 命令
pipx install git+https://github.com/sogeisetsu/pixel-logo-toolkit.git

# 或者用 pip
pip install git+https://github.com/sogeisetsu/pixel-logo-toolkit.git

# 或者从源码装（开发时用 -e）
git clone https://github.com/sogeisetsu/pixel-logo-toolkit.git
cd pixel-logo-toolkit
pip install -e .
```

> 只克隆仓库**不会**产生 `pixellogo` 命令。不想安装时，可以在仓库根目录用
> `PYTHONPATH=src python -m pixellogo ...` 直接跑（本文其余示例都可用这种写法替代）。

唯一运行时依赖是 Pillow，Python 需 ≥ 3.9。

### 2.2 验证安装

```console
$ pixellogo --version
pixellogo 0.3.0

$ pixellogo --list modes
poster     3:4  竖版海报（小红书封面）                     输出 1080×1440
card       4:3  横版卡片（文章头图 / PPT）                 输出 1440×1080
banner     2:1  仓库横幅（GitHub 预览图）                  输出 1280×640
slide     16:9  宽屏幻灯片（16:9）                         输出 1920×1080
square     1:1  方形图片（社交头像 / 九宫格）              输出 1080×1080
```

### 2.3 出第一张图

```bash
pixellogo -t "REA" -s "REVERSE ENGINEER" -d "One CLI for agents"
```

```console
$ ls out/
REA-poster.png  REA-poster.svg
```

默认行为可以一句话记住：**`poster` 画布、`terminal` 配色、逻辑尺寸 540×720 放大 2 倍、PNG + SVG 各一份、写到 `out/` 目录、文件名 = 标题-画布**。

### 2.4 三条最常用的调整

```bash
pixellogo -t "PIXEL" -m slide            # 换画布：1920×1080
pixellogo -t "PIXEL" -p cyber            # 换配色：暗夜赛博
pixellogo -t "PIXEL" -o cover.png        # 指定文件名（同时按需生成 cover.svg）
```

### 2.5 不带参数会发生什么

```bash
pixellogo            # 打印帮助，退出码 0
pixellogo help       # 同上
pixellogo -h         # 同上
```

---

## 三、心智模型：一条命令做了什么

### 3.1 四层配置，后者覆盖前者

```
内置默认  <  风格预设 -p  <  配置文件 -c  <  命令行（含 --set）
```

举例：配置文件写了 `"mode": "banner"`，命令行再加 `-m slide`，结果是 `slide`；`--set colors.accent=#FF3D81`
优先级与命令行参数相同，且**后写的 `--set` 覆盖先写的**。

想看清合并结果，用 `--dry-run`——只打印配置，不渲染、不写盘：

```bash
pixellogo -c examples/og.jsonc -m slide --set colors.accent=#FF3D81 --dry-run
```

```console
{
  "mode": "slide",
  "canvas": { "logical": [960, 540], "output": [1920, 1080], "scale": 2 },
  "preset": "cyber",
  "content": { "title": "像素工具包", "subtitle": ["PIXEL LOGO TOOLKIT"], ... },
  "colors": { "bg": "#0D1117", "fg": "#E6EDF3", "primary": "#00E5A0", "accent": "#FF3D81", ... },
  "layout": { "align": "auto", "margin": 0.06, "divider": "line", "titleSize": "auto", ... },
  "output": { "path": "out", "format": ["png", "svg"] }
}
```

> `--dry-run` 的快照是**不完整**的：不含 `pattern`、`tracking`、`leading`、`uppercase`、`lang`、`fonts`。
> 它也不做排版，所以**看不到**溢出告警（那条告警在渲染阶段才产生）。它也会输出缺字告警（见 9.4）。

### 3.2 一次渲染的五个阶段

```
解析参数 → 合并与校验 → 排版出 Scene（纯几何） → 后端写盘（PNG / SVG） → 打印结果
```

关键在第三阶段：文字先被栅格化成**二值掩膜**，再按行合并成**整数坐标矩形**，所有绘制都是矩形。
所以 PNG 与 SVG 来自同一份几何数据，像素级一致；放大后边缘仍是方块，不会出现灰边。

这也解释了几条常见疑问：为什么只有纯色背景、为什么不能旋转文字、为什么 `--scale` 只能是整数（见第九节）。

---

## 四、参数速查

### 4.1 通用

| 参数 | 取值 | 说明 |
| --- | --- | --- |
| `-h, --help` | — | 打印帮助；`pixellogo help` 等价 |
| `-V, --version` | — | 打印 `pixellogo 0.3.0` |
| `--ui-lang` | `auto` / `en` / `zh` | 只影响 **CLI 文案**，不影响出图字形 |

### 4.2 内容

| 参数 | 可重复 | 默认 | 配置键 |
| --- | --- | --- | --- |
| `-t, --title` | 否 | 无（**必填**） | `title` |
| `-s, --subtitle` | 是，每次一行 | 空 | `subtitle` |
| `-d, --desc` | 是，每次一行 | 空 | `desc` |
| `-e, --eyebrow` | 否 | 空 | `eyebrow` |
| `--badge` | 否 | 空 | `badge` |

### 4.3 风格

| 参数 | 取值 | 默认 | 配置键 |
| --- | --- | --- | --- |
| `-p, --preset` | 十套预设，见 5.3 | `terminal` | `preset` |
| `--bg` `--fg` `--primary` `--accent` `--shadow-color` | `#RGB` / `#RRGGBB` | 取预设 | `colors.*` |
| `--shadow-offset` | 0–4 整数 | 1 | `layout.shadowOffset` |
| `--title-size` | 像素 | 自动 | `layout.titleSize` |
| `--tracking` | 0.5–1.5 | 1.0 | `layout.tracking` |
| `--leading` | 0.8–2.0 | 1.0 | `layout.leading` |
| `--uppercase` | 开关 | 关 | `layout.uppercase` |
| `--lang` | `zh-hans` / `zh-hant` / `ja` / `ko` | `zh-hans` | `lang` |
| `--font-title` `--font-sub` `--font-body` | 内置字体键或 `.ttf` 路径 | 取预设 | `fonts.*` |

### 4.4 排版

| 参数 | 取值 | 默认 | 配置键 |
| --- | --- | --- | --- |
| `--align` | `auto` / `left` / `center` | `auto` | `layout.align` |
| `--vertical` | `auto` / `top` / `center` | `auto` | `layout.vertical` |
| `--margin` | 0 ≤ x < 0.4 | 0.06 | `layout.margin` |
| `--divider` | `auto` / `line` / `dash` / `block` / `none` | `auto`（跟随预设） | `layout.divider` |
| `--divider-width` | 0.05–1.0 | 0.42 | `layout.dividerWidth` |
| `--motif` | `auto` / `none` / `blocks` | `auto` | `layout.motif` |
| `--bg-pattern` | `none` / `grid` / `dots` / `scanlines` | `none` | `layout.pattern` |
| `--wrap` / `--no-wrap` | 成对开关 | 开（折行） | `layout.wrap` |

### 4.5 输出

| 参数 | 取值 | 默认 | 配置键 |
| --- | --- | --- | --- |
| `-m, --mode` | 五种画布 + 别名 | `poster` | `mode` |
| `--size` | `宽x高` | 无 | `size`（优先于 `mode`） |
| `--scale` | 1–8 整数 | 2 | `scale` |
| `-f, --format` | `png` / `svg` / `both` | `both` | `format` |
| `-o, --out` | 目录或文件 | `out` | `out` |

### 4.6 配置与其他

| 参数 | 说明 |
| --- | --- |
| `-c, --config PATH` | 读 JSONC 配置文件 |
| `--set KEY=VALUE` | 点路径覆盖，可重复，如 `--set colors.primary=#FF3D81` |
| `--dry-run` | 只打印合并后的配置与告警 |
| `--json` | 结果以 JSON 数组输出 |
| `--open` | 用系统默认程序打开第一张图 |
| `--list presets\|modes\|fonts` | 列出内置枚举后退出 |

---

## 五、逐项详解

### 5.1 内容字段

```bash
pixellogo \
  -e "TOOLKIT / 2026" \
  -t "像素工具包" \
  -s "PIXEL LOGO TOOLKIT" -s "FOR AGENTS" \
  --badge NEW \
  -d "8-bit 风格图像生成器" -d "PNG / SVG 双格式输出"
```

- `-t` 必填，缺失时报错退出码 2。
- `-s` / `-d` **每次给一行**；重复给几行就渲染几行，顺序即参数顺序。
- `-e` 小字标签在标题上方，`--badge` 是右上角实心徽标。小字标签超宽会自动折行；徽标是实心框，不折行，超宽时自动缩小字号。
- 空行会被丢弃（`"  "` 不算一行）。

**换行的真实行为（容易踩坑）**：标题与每一行的内容只识别**真实换行符**，不认字面量 `\n`。

```bash
# 正确：bash 里用 $'...' 让 \n 变成真换行
pixellogo -t $'PIXEL\nLOGO'

# 无效：会原样输出一个反斜杠加 n
pixellogo -t "PIXEL\nLOGO"

# 配置文件里写 JSON 转义即可（这里是真换行符）
pixellogo -c examples/rea.jsonc
```

> 帮助文案里写的 “`\n` starts a new line” 指的是配置文件中的 JSON 转义写法；命令行请用 `$'...'`。

### 5.2 画布与尺寸

| 画布 | 逻辑尺寸 | 默认输出（×2） | 比例 | 排版特征 |
| --- | --- | --- | --- | --- |
| `poster` | 540×720 | 1080×1440 | 3:4 | 居中，标题撑满宽度 |
| `card` | 720×540 | 1440×1080 | 4:3 | 左对齐，垂直居中 |
| `banner` | 640×320 | 1280×640 | 2:1 | 左对齐，右下角阶梯装饰 |
| `slide` | 960×540 | 1920×1080 | 16:9 | 左对齐，留白多 |
| `square` | 540×540 | 1080×1080 | 1:1 | 完全居中 |

```bash
pixellogo -t "PIXEL" -m slide           # 1920×1080
pixellogo -t "PIXEL" -m 16:9            # 别名，等价于 slide
pixellogo -t "PIXEL" --size 1200x900    # 逻辑 1200×900 → 输出 2400×1800
pixellogo -t "PIXEL" --size 1200x900 --scale 1   # 输出就是 1200×900
```

三条必须记住的规则：

1. **`--size` 是逻辑尺寸**，输出还要再乘 `--scale`（默认 2）。所以 `--size 1200x900` 出的是 2400×1800，不是 1200×900。
2. **`--size` 优先于 `-m`**，一旦给出 `--size`，`-m` 被忽略（`--dry-run` 里 `mode` 会显示 `custom`）。
3. 画布最小 64×64，`--scale` 只接受 1–8 的整数。

别名（旧配置可直接沿用）：`xhs` / `xiaohongshu` / `red` / `redbook` / `3:4` / `portrait` / `story` → `poster`；
`4:3` / `landscape` → `card`；`og` / `github` / `repo` / `social` / `open-graph` / `2:1` → `banner`；
`16:9` / `wide` / `widescreen` → `slide`；`1:1` / `avatar` → `square`。

### 5.3 风格预设与配色

```console
$ pixellogo --list presets
terminal   复古终端（参考原味）       底 #EEF1F6 主 #02ADFB 强调 #FF6104 对比度 14.6
cyber      暗夜赛博                   底 #0D1117 主 #00E5A0 强调 #FF3D81 对比度 16.0
arcade     复古街机                   底 #1B1F27 主 #FFD200 强调 #FF5F1F 对比度 15.1
candy      柔和糖果                   底 #FFF5F7 主 #FF7EB6 强调 #4ECDC4 对比度 12.3
minimal    极简专业                   底 #F8FAFC 主 #2563EB 强调 #F97316 对比度 17.1
noir       黑白纪实                   底 #F4F4F5 主 #18181B 强调 #E11D48 对比度 16.1
forest     森林苔绿                   底 #F0F4EF 主 #2F6B3C 强调 #D97706 对比度 13.3
sunset     黄昏日落                   底 #2B1B2F 主 #FF8A3D 强调 #FFD166 对比度 13.7
ocean      深海青蓝                   底 #E8F1F5 主 #0077B6 强调 #2A9D8F 对比度 12.4
paper      纸本手账                   底 #F5EEE1 主 #8C3B2E 强调 #C9822E 对比度 12.3
```

「对比度」是前景与背景的 WCAG 对比度，十套都在 12:1 以上（远高于 AA 要求的 4.5:1）。
一套预设包含六项：背景色、文字色、主色（标题）、强调色（分隔线与徽标）、投影色，以及字体配对与投影强度。

单色覆盖，优先级高于预设、彼此独立：

```bash
pixellogo -t "PIXEL" -p forest --accent "#FF3D81"
pixellogo -t "PIXEL" --bg "#0B1020" --fg "#E6EDF3" --primary "#7C3AED"
```

色值只接受 `#RGB` 或 `#RRGGBB`；写成 `#ffff` 或 `red` 会直接报错退出码 2。

### 5.4 排版控制

| 参数 | 作用 | 细节 |
| --- | --- | --- |
| `--align` | 水平对齐 | `auto` 跟随画布：`poster`/`square` 居中，其余左对齐 |
| `--vertical` | 垂直锚点 | `auto` 时竖版居中、`custom` 宽版居顶；`top` 时内容从安全边距开始 |
| `--margin` | 安全边距 | 相对画布**短边**的比例，0.06 表示短边的 6% |
| `--divider` | 分隔线样式 | `line`（带端点方块）/ `dash` / `block` / `none`；`auto` 跟随预设 |
| `--divider-width` | 分隔线长度 | 相对文本区宽度的比例，0.42 = 42% |
| `--motif` | 右下角阶梯装饰 | `auto` 只在 `banner` 开启；开启时会从文本区让出约 26% 宽度 |
| `--bg-pattern` | 背景纹理 | `grid` 方格纸 / `dots` 点阵 / `scanlines` 扫描线，颜色是底与字的 10% 混色 |
| `--title-size` | 固定标题字号 | 显式指定后**只允许缩小，不再放大** |
| `--tracking` | 字距倍率 | 0.9 更紧凑，1.1 更松散 |
| `--leading` | 行高倍率 | 只影响多行之间的间距 |
| `--uppercase` | 全部转大写 | 对中文无影响 |
| `--shadow-offset` | 投影格数 | 0 关闭投影；投影由矩形整体偏移派生，不改字形 |
| `--wrap` / `--no-wrap` | 自动折行 | 默认开启：副标题、说明、小字标签超宽时按文本区宽度折行；`--no-wrap` 回到「一行硬挤」的旧行为 |

```bash
pixellogo -t "PIXEL" --tracking 0.88 --leading 1.2 --uppercase
pixellogo -t "PIXEL" --align left --vertical top --divider dash
pixellogo -t "PIXEL" --shadow-offset 0            # 平面风格，无投影
pixellogo -t "GRID" -p forest --bg-pattern grid
pixellogo -t "PIXEL" -s "<很长的一行副标题>" --no-wrap   # 强制不折行
```

标题字号是**双向自适应**的：太长就缩小直到放进文本区，太短就放大到接近撑满（上限约为画布高的 42%），
收放都以整数像素为步长。副标题与说明则先**折行**、再在总高放不下时**缩小字号**（下限 9px），
具体边界见 [9.2](#92-副标题与说明自动折行字号下限-9px) 与 [9.3](#93-行数与高度溢出时先缩字号再告警)。

### 5.5 字体与字形变体

| 内置键 | 字体 | 角色 | 覆盖 |
| --- | --- | --- | --- |
| `press-start-2p` | Press Start 2P | 标题（默认） | 拉丁 |
| `silkscreen` | Silkscreen | 副标题（默认） | 拉丁，无小写 |
| `pixelify` | Pixelify Sans | 说明文字（默认） | 拉丁，含大小写 |
| `ark-pixel` | Ark Pixel 12px Proportional | 中日韩 | 汉字、假名、拉丁 |

**混排规则**：一行里只要出现中日韩字符，整行切换到中文字形，并额外加粗一档（`cjkBold`），
保证同一行不会出现两种笔画粗细。

**字形变体**：`zh-hans` 随包内置，其余按需下载到 `~/.pixellogo/fonts`。

```console
$ pixellogo fonts
zh-hans  随包内置         Ark Pixel 12px (zh-hans)
zh-hant  已下载           Ark Pixel 12px (zh-hant)
ja       已下载           Ark Pixel 12px (ja)
ko       已下载           Galmuri 11px (ko)

字体目录：C:\Users\you\.pixellogo\fonts
按需安装：pixellogo fonts install <zh-hant|ja|ko>

$ pixellogo fonts install ja
$ pixellogo -t "ピクセル" --lang ja
```

- `--lang` 选的是**字形变体**，`--ui-lang` 选的是**界面语言**，两者互不影响：`--ui-lang en --lang ja` 是「英文界面 + 日文字形」。
- `--lang` 接受 `zh-hans` / `zh-hant` / `ja` / `ko`，也接受 `zh-cn`、`zh-tw`、`jp`、`kr` 等写法。
- 韩语用 Galmuri 而不是 Ark Pixel：Ark Pixel 的 `ko` 版不含谚文。
- 内容里完全没有中日韩字符时，缺变体字体不算错误。
- 也可以用自己的像素字体：`--font-title /path/to/font.ttf`（同样支持 `--font-sub`、`--font-body`）。

### 5.6 `fonts` 子命令

| 写法 | 行为 | 退出码 |
| --- | --- | --- |
| `pixellogo fonts` / `fonts list` | 列出四个变体的状态（随包内置 / 已下载 / 缺失）与字体目录 | 0 |
| `pixellogo fonts install <lang>` | 联网下载并安装该变体 | 0；失败 2 |
| `pixellogo fonts install`（缺语言） | 提示缺少语言参数 | 2 |
| `pixellogo fonts xxx` | 提示只支持 `list` / `install` | 2 |

---

## 六、配置文件（JSONC）

### 6.1 基本用法

```bash
pixellogo -c examples/og.jsonc                 # 全部从文件读
pixellogo -c examples/og.jsonc -m card         # 命令行覆盖画布
pixellogo -c examples/og.jsonc --set colors.accent=#FF3D81
```

JSONC = JSON + `//` 行注释、`/* */` 块注释、尾逗号。字符串里的 `//` 与 `,}` 不会被误判。

### 6.2 完整键表

| 键 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `mode` | string | `poster` | 画布 |
| `size` | `"1200x900"` | — | 自定义画布，优先于 `mode` |
| `preset` | string | `terminal` | 配色预设 |
| `title` | string | 必填 | 主标题，可含真实换行 |
| `subtitle` | string 或 string[] | `[]` | 每个元素一行 |
| `desc` | string 或 string[] | `[]` | 同上 |
| `eyebrow` | string | `""` | 标题上方小字 |
| `badge` | string | `""` | 右上角徽标 |
| `lang` | string | `zh-hans` | 字形变体 |
| `colors` | object | 取预设 | `bg` `fg` `primary` `accent` `shadow` |
| `fonts` | object | 取预设 | `title` `sub` `body` |
| `layout` | object | 见下 | 排版 |
| `output` | object | — | `dir` / `path` / `scale` / `formats` |
| `scale` `out` `format` | 顶层简写 | — | 等价于 `output` 下的同名项 |

`layout` 子键：`align` `vertical` `margin` `divider` `dividerWidth`（也可写 `divider-width`）
`titleSize`（`title-size`）`shadowOffset`（`shadow-offset`）`motif` `pattern` `tracking` `leading`
`uppercase` `wrap` `cjkBold`（`cjk-bold`）。

其中 `wrap` 是布尔开关，默认 `true`；写 `"wrap": false` 即关闭自动折行。配置里写成字符串 `"false"` / `"off"` / `"0"` 也会按关闭处理（`uppercase` 同样如此）。

```jsonc
// examples/rea.jsonc
{
  "mode": "poster",
  "preset": "terminal",
  "title": "REA",
  "subtitle": ["REVERSE ENGINEER", "ANYTHING"],
  "desc": ["One CLI + MCP server for agents", "From binaries to websites"],
  "layout": { "align": "center", "divider": "line", },
  "output": { "dir": "out", },
}
```

### 6.3 批量：顶层数组

```jsonc
[
  { "mode": "poster", "title": "REA", "subtitle": ["REVERSE ENGINEER"] },
  { "mode": "banner", "title": "REA", "desc": ["Repository social preview"] }
]
```

```bash
pixellogo -c examples/batch.jsonc -o out/ -f png --json
```

`-o` 对所有项生效；同名文件自动加序号（`REA-poster-2.png`），不会互相覆盖。空数组会报错退出 2。

### 6.4 `--set` 的取值转型

`--set KEY=VALUE` 先尝试 `json.loads`，失败则保留字符串：

| 写法 | 结果 |
| --- | --- |
| `--set layout.margin=0.1` | 数字 0.1 |
| `--set layout.shadowOffset=2` | 整数 2 |
| `--set layout.uppercase=true` | 布尔 true |
| `--set colors.primary=#FF3D81` | 字符串（`#` 开头不是合法 JSON，按原样保留） |
| `--set title="A B"` | 字符串 A B（带引号才会去掉引号） |

未知键（如 `--set foo.bar=1`）不会报错，但会在合并结果里被忽略或触发告警。

---

## 七、输出、路径与界面语言

### 7.1 `-o` 与 `-f` 的组合

| `-o` 是 | `-f` | 结果 |
| --- | --- | --- |
| 目录 `out/` | `png` | `out/<标题>-<画布>.png` |
| 目录 `out/` | `both` | `out/<标题>-<画布>.png` + `.svg` |
| 文件 `cover.png` | `png` | `cover.png` |
| 文件 `cover.png` | `both` | `cover.png` + `cover.svg` |
| 文件 `cover.png` | `svg` | `cover.svg`（格式由 `-f` 决定，文件名主干保留） |

命名规则：标题里的空白与 `\ / : * ? " < > |` 替换成 `-`，连续 `-` 合并，中日韩字符保留，最长 60 字符。
目标目录不存在时会自动创建。

### 7.2 界面语言

CLI 的**全部文案**（帮助、`--list` 表格、`fonts` 输出、告警、报错）都有中英两版。

优先级：`--ui-lang` > 环境变量 `PIXELLOGO_UI_LANG` > `LC_ALL` / `LC_MESSAGES` / `LANG` / `LANGUAGE` >
Windows 系统界面语言 > 英语。`C` / `POSIX` 视为英语，非中文一律回退英语。

```bash
pixellogo --help                     # 跟随终端语言
pixellogo --ui-lang en --help        # 强制英文
PIXELLOGO_UI_LANG=en pixellogo --list presets    # 用环境变量长期固定
```

---

## 八、脚本化：JSON 结果、退出码与 Python API

### 8.1 `--json`

```console
$ pixellogo -t REA -m banner -f both -o assets/ --json
[
  {
    "files": ["assets\\REA-banner.png", "assets\\REA-banner.svg"],
    "mode": "banner",
    "width": 1280,
    "height": 640,
    "format": ["png", "svg"]
  }
]
```

数组长度等于批量项数；`width` / `height` 是**输出尺寸**（已乘 `scale`）。

### 8.2 退出码与输出流

| 场景 | stdout | stderr | 退出码 |
| --- | --- | --- | --- |
| 成功 / `--help` / `--version` / `--list` / 裸执行 | 结果或帮助 | — | 0 |
| 参数非法（未知参数、非法枚举、缺值） | — | 用法 + 报错 | 2 |
| 配置错误（缺标题、非法色值、越界、未知格式、配置文件不存在或语法错） | — | 报错 + `--help` 提示 | 2 |
| 渲染写盘失败 | — | 报错 | 2 |
| 缺 Pillow（渲染链路导入失败） | — | 报错 | 2 |
| 未知配置键 / 缺字 | 正常结果 | 一行 `提示：…` | 0（继续渲染） |

三类消息的前缀不同，写脚本时不要混用判断：

| 类型 | 中文前缀 | 英文前缀 |
| --- | --- | --- |
| 告警（未知键、缺字） | `pixellogo: 提示：` | `pixellogo: warning: ` |
| 参数解析错误（argparse） | `pixellogo: 错误：` | `pixellogo: error: ` |
| 程序自身抛出的配置 / 渲染错误 | `pixellogo: `（后直接跟原因） | `pixellogo: ` |

脚本里判断成功只看**退出码**，不要解析 stdout。

### 8.3 CI 用法示例

```bash
# 一次生成整套社交素材，任一失败即中断
set -e
pixellogo -t "像素工具包" -m banner -o .github/ -f png --ui-lang en
pixellogo -c assets/social.jsonc -o assets/social/ -f both --json > build/social.json
```

```yaml
# GitHub Actions
- run: pip install .
- run: pixellogo -c assets/ci.jsonc -o public/ -f png
```

### 8.4 Python API 与 CLI 的对应关系

```python
from pixellogo import render, render_many, make_image, make_scene, to_svg_text

paths = render(title="REA", mode="banner", preset="cyber", format="png", out="out/")
image = make_image(title="REA", mode="square", scale=1)   # 只出图，不写盘
scene = make_scene(title="REA", mode="poster")           # 只出几何
svg   = to_svg_text(title="REA", mode="slide")           # 只出 SVG 源码
render_many([{"title": "A", "mode": "poster"}], out="out", format="png")
```

关键字参数与 JSONC 键**完全同名**，所以配置文件怎么写，这里就怎么传：

```python
render(
    title="像素工具包",
    subtitle=["PIXEL LOGO TOOLKIT"],
    colors={"primary": "#8C3B2E", "accent": "#C9822E"},
    layout={"align": "left", "divider": "dash", "pattern": "grid"},
    out="out/",
)
```

---

## 九、能力边界与限制

这一节列的每一条都可以复现，数字是**实测值**（`terminal` 预设、默认字体、`scale` 不影响版面）。
架构层面的成因见 [`architecture.md` 第五节](architecture.md#五架构决定的固有限制)。

### 9.1 标题：会自动缩放，但有下限

标题按可用宽度双向自适应，最小字号 10px，最大约为画布高的 42%。字数与最终字号的实测关系：

| 画布 | 3 字 | 5 字 | 8 字 | 12 字 |
| --- | --- | --- | --- | --- |
| `poster` | 158px | 94px | 58px | 40px |
| `card` | 206px | 123px | 77px | 50px |
| `banner` | 134px | 84px | 54px | 35px |
| `slide` | 226px | 154px | 97px | 64px |
| `square` | 148px | 85px | 55px | 36px |

**实用结论**：主标题控制在 **5 个字符以内**最稳；超过 12 字符时字号已掉到 40px 以下，像素网格开始糊，
不如改成多行（`-t $'FIRST\nSECOND'`）或换更宽的画布（`slide`）。缩到最小字号 10px 时，
`poster` 能塞约 45 个字符、`slide` 约 75 个，但那个字号已经没有视觉意义。

### 9.2 副标题与说明：自动折行，字号下限 9px

副标题与说明行的字号由画布高度决定（如 `poster` 副标题 30px、说明 24px）。**单行超过文本区宽度时自动折成多行**，
不再被画布裁掉：

```bash
# 这一行在 card 上放不下，会被折成两行（而不是右半截消失）
pixellogo -t TEST -m card -s "自动折行之后每一行都不会超出文本区域宽度限制这是用来验证折行是否生效的一整段中文副标题"
```

规则由 [`text.wrap_line()`](../src/pixellogo/text.py) 实现：

- 中日韩字符与全角标点**逐字可断**——中文没有空格，也能折；
- 拉丁文按空格成词，断点吃在空格上，不会把单词劈开；
- 单个词本身就比文本区还宽（长 URL、长哈希）时按字符硬切，保证一定放得下；
- 折行只发生在**你给的一行之内**，`-s` 重复几次就是几个段落，段落之间不会被合并。

折行前每行能放多少字（超过就会折）：

| 画布 | 副标题每行 | 说明每行 |
| --- | --- | --- |
| `poster` | 18 | 25 拉丁 / 19 汉字 |
| `card` | 30 | 44 拉丁 / 34 汉字 |
| `banner` | 37 | 51 拉丁 / 39 汉字 |
| `slide` | 38 | 55 拉丁 / 42 汉字 |
| `square` | 21 | 31 拉丁 / 24 汉字 |

想保持「一行硬挤」的旧行为（例如刻意让文字贴近边缘），加 `--no-wrap`，或写 `"layout": {"wrap": false}`。

### 9.3 行数与高度：溢出时先缩字号，再告警

折行会让行数变多，行数太多时总高会超过可用高度。此时排版层按总高比例**缩小副标题与说明的字号**并重新折行，
下限 `MIN_TEXT_SIZE = 9px`；缩到 9px 仍放不下，才在 stderr 打印告警，并照常出图（超出部分由画布裁切）。

实测各画布在「标题 3–4 字 + 全为副标题」条件下的行数上限（超过即触发告警）：

| 画布 | 最多行数（缩到 9px 后） |
| --- | --- |
| `poster` | 约 30 行 |
| `square` | 约 20 行 |
| `card` | 约 16 行 |
| `slide` | 约 13 行 |
| `banner` | 约 8 行 |

上限与标题大小相关：标题越大，留给副标题的高度越少。极端情况下（例如 `poster` 上写 40 行副标题）会看到：

```console
$ pixellogo -c many-lines.jsonc        # 40 行副标题
pixellogo: 提示：内容高 810px，可用高度只有 656px，字号已缩到 9px，超出部分会被画布裁切
many-lines-poster.png  (1080×1440)
```

退出码仍是 0——告警不阻断批量出图。要避免这条告警，换更高的画布、减少行数，或用 `-d` 把长文案拆到说明区。

### 9.4 字形：内置中文字体覆盖约 89%，缺字渲染成方块

- 内置 `ArkPixel-zh-hans.ttf` 覆盖基本区汉字 **18,648 / 20,902（89.2%）**，随机抽样 400 个汉字缺 38 个（约 9.5%）。
- 已知缺失的常用字包括 **「即」(U+5373)、「然」(U+7136)、「餐」(U+9910)**。
- 缺字会渲染成空心方块（`.notdef`），**不会**自动回退到系统字体。
- 从 0.3.0 起，缺字走「整行选缺字最少的字体」策略，并且会在 stderr 提示：

```console
$ pixellogo -t ZIG -d "compile time 即运行时" -m card -p forest -f png
pixellogo: 提示：字体 ArkPixel-zh-hans.ttf 缺少字形：即，这些字会渲染成方块
out/ZIG-card.png  (1440×1080)
```

规避方式，按推荐顺序：

1. 换一个含该字形的数码字体：`--font-title /path/to/font.ttf`（`--font-sub` / `--font-body` 同理）；
2. 改写文案，避开缺字（如「即运行时」→「运行时」）；
3. 出图前先自查：`--dry-run` 会把缺字告警一起打出来，不必先渲染再发现。

### 9.5 视觉风格（结构性限制）

- **只支持纯色背景**：不能贴图片、不能做渐变、不能半透明。`--bg-pattern` 是用纯色矩形拼出来的纹理。
- **没有文字特效**：无描边、无外发光、无斜体、无旋转，也不能加粗（中文字形的加粗由 `cjkBold` 比例决定，不收参数开关）。
- **一行只能用一款字体**：中英混排会整行切成中文字形，无法在一行内混用两种笔画粗细。
- **不能叠加多个装饰**：`--motif` 只有一种阶梯造型，徽标只有一个。

### 9.6 尺寸与输出

- 画布最小 64×64，最大没有硬性校验，但超过约 8000px 的 `--size` 会显著变慢并吃满内存。
- `--scale` 只接受 1–8 的整数；`--scale 1.5` 会报错。
- `--scale` 只放大输出，不改变版面（逻辑尺寸不变，字距行距比例一致）。
- `--size` 是**逻辑尺寸**，输出 = 逻辑 × `scale`，这是最容易误读的一点。

### 9.7 参数边界（覆盖能力的极限）

| 现象 | 原因 |
| --- | --- |
| `--align auto` 改了配置里的 `left` 却没生效 | `auto` 会被过滤掉，命令行**无法**把配置文件里的具体值改回 auto |
| `--vertical auto` / `--divider auto` / `--motif auto` 同样无效 | 同上 |
| `--uppercase` 打开了就关不掉 | 它是 `store_true` 开关，只能开；折行则做成了成对的 `--wrap` / `--no-wrap` |
| `-e ""` / `--badge ""` 清不掉配置里的值 | 空字符串在合并时被丢弃 |
| `-t "A\nB"` 没有换行 | 只认真实换行符，见 5.1 |
| `--list` 与 `fonts` 谁优先 | `fonts` 子命令优先于 `--list` |

### 9.8 工程与环境

- **没有交互模式**：没有任何问答式 TUI；唯一的副作用动作是 `--open` 打开图片、`fonts install` 联网下载。
- **没有独立可执行文件**：必须有 Python 环境（便携包也只是附带 `pixellogo.cmd` / `.sh` 包装脚本）。
- **JSON Schema 已过时**：`src/pixellogo/schema/pixellogo.schema.json` 的 `mode` / `preset` 枚举落后于当前实现，
  编辑器按它补全会误报。它是便利件，真正的校验在程序内部。
- **缺少 Pillow 时纯查询命令仍可用**：`--version` / `--help` / `--list` 不需要 Pillow，渲染才需要。

---

## 十、排错手册

| 症状 | 原因 | 处置 |
| --- | --- | --- |
| 文字变成一排空心方块 | 字体缺该字形 | 看 stderr 的「缺少字形」提示；换 `--font-*` 指定字体，或改写文案（9.4） |
| `pixellogo: command not found` | 只克隆了仓库没安装 | `pip install .`；或 `PYTHONPATH=src python -m pixellogo ...`；Windows 检查 `<python>\Scripts` 是否在 `PATH` |
| `渲染需要 Pillow` | 环境里没装 Pillow | `pip install pillow` |
| 标题太小 | 画布太窄或标题太长 | 换更宽画布（`-m slide`）、减小 `--margin`、或 `--title-size` 显式指定 |
| 输出尺寸是预期的两倍 | `--size` 是逻辑尺寸 | 加 `--scale 1`，或把 `--size` 按一半写 |
| 副标题/说明被切掉 | 已按文本区宽度自动折行；仍被裁说明总高超过画布，stderr 有溢出告警 | 减少行数或换更大的画布；想看旧行为用 `--no-wrap`（9.2、9.3） |
| `--set` 的值变成了字符串 | `json.loads` 解析失败即保留原串 | 布尔写 `true`，数字直接写，字符串需要时加引号 |
| 批量出图被覆盖 | 其实不会重叠 | 同名自动加 `-2` / `-3`，检查 `-o` 是否指到了不同目录 |
| 编辑器把配置标红 | schema 过时 | 忽略，或移除 `"$schema"` 行 |
| 中文帮助没出现 | 终端 locale 不是中文 | `--ui-lang zh`，或设 `PIXELLOGO_UI_LANG=zh` |

---

## 附录

### A. 环境变量

| 变量 | 作用 |
| --- | --- |
| `PIXELLOGO_UI_LANG` | CLI 文案语言（`en` / `zh` / `auto`） |
| `PIXELLOGO_FONT_DIR` | 字形变体的缓存目录，默认 `~/.pixellogo/fonts` |
| `PIXELLOGO_FONT_MIRROR` | 字体包下载镜像前缀 |
| `LC_ALL` / `LC_MESSAGES` / `LANG` / `LANGUAGE` | locale 兜底，用于自动判断界面语言 |

### B. 画布别名总表

| 别名 | 指向 |
| --- | --- |
| `xhs` `xiaohongshu` `red` `redbook` `3:4` `3x4` `portrait` `story` | `poster` |
| `4:3` `4x3` `landscape` | `card` |
| `og` `github` `repo` `social` `open-graph` `2:1` `2x1` | `banner` |
| `16:9` `16x9` `wide` `widescreen` | `slide` |
| `1:1` `1x1` `avatar` | `square` |

### C. 语言别名

`zh` `zh-cn` `zh_hans` → `zh-hans`；`zh-tw` `zh-hk` `zh_hant` → `zh-hant`；`jp` `ja-jp` → `ja`；`kr` `ko-kr` → `ko`。

### D. 参数字母序索引

`--accent` `--align` `--badge` `--bg` `--bg-pattern` `-c/--config` `-d/--desc` `--divider` `--divider-width`
`--dry-run` `-e/--eyebrow` `--fg` `--font-body` `--font-sub` `--font-title` `-f/--format` `-h/--help`
`--json` `--lang` `--leading` `--list` `--margin` `-m/--mode` `--motif` `--no-wrap` `--open` `-o/--out`
`-p/--preset` `--primary` `--scale` `--set` `--shadow-color` `--shadow-offset` `--size` `-s/--subtitle`
`-t/--title` `--title-size` `--tracking` `--ui-lang` `--uppercase` `-V/--version` `--vertical` `--wrap`

### E. 相关文档

- [`architecture.md`](architecture.md) —— 仓库文件架构、分层与数据流。
- [`gallery.md`](gallery.md) —— 40 张成品与逐条命令。
- [`style-spec.md`](style-spec.md) —— 风格不变式与提示词库。
