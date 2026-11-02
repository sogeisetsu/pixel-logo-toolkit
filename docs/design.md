# `pixellogo` CLI —— 设计与实施计划

> 目标：把当前「改脚本里的 `CONTENT` 列表再跑 Python」的用法，变成一个可安装、可脚本化、可批量的命令行工具。
> 输入是一份 JSON / JSONC 配置或一串命令行参数，输出是像素风格的图片。

---

## 一、结论先行

| 决策项       | 选择                                        | 理由                                                     |
| --------- | ----------------------------------------- | ------------------------------------------------------ |
| 语言        | Python 3.9+                               | 现有 `make_pixellogo.py`、`tools/*.py` 全是 Python + Pillow，能力可直接复用 |
| 打包        | `pyproject.toml` + console_scripts        | `pipx install .` 后直接得到 `pixellogo` 命令，跨平台分发              |
| 默认渲染      | Pillow 直出 PNG（去掉 Chrome 依赖）               | 当前靠 Chrome headless 截图，CI 与无浏览器环境不可用；Pillow 逐矩形填充结果等价且确定性更强 |
| 矢量输出      | 同一份图元数据另写 SVG                            | 一份几何、两个渲染后端，保证 SVG 与 PNG 像素级一致                         |
| 配置语言      | JSONC（自带 80 行解析器，不引第三方依赖）                 | 注释 / 尾逗号对人工维护配置很重要，且不想为它增加安装体积                         |
| 参数优先级     | 默认值 < preset < 配置文件 < CLI 参数              | 与主流 CLI 一致，便于"配置文件定基线、命令行临时改一项"                         |

---

## 二、三种输出模式（画布规格）

| `--mode` | 画布（逻辑 1x）   | 输出（2x）       | 用途                      |
| -------- | ----------- | ------------ | ----------------------- |
| `xhs`    | 540 × 720   | 1080 × 1440  | 小红书竖版封面（3:4）            |
| `4:3`    | 720 × 540   | 1440 × 1080  | 通用头图 / PPT / 文章配图（4:3） |
| `og`     | 640 × 320   | 1280 × 640   | GitHub Repository Open Graph 预览图（2:1） |
| `custom` | `--size WxH` | `W×scale`    | 非常规需求兜底                 |

**三种模式的排版不是同一套模板缩放**，而是各自独立的布局策略：

- **`xhs`（竖版）**：内容块垂直居中；标题允许 2 行；副标题与说明各自成组；装饰线宽度约为内容宽 45%。需预留顶部 12%、底部 15% 的安全区（小红书信息流会裁切）。
- **`4:3`（横版）**：左对齐 + 顶部锚定，纵向留白靠间距呼吸，不做垂直居中（居中会在宽画布上显得空）。
- **`og`（宽幅）**：文字块限定在左侧 62% 宽，右侧留给像素图形 / 徽标；标题字号上限比横版小一档，保证在 GitHub 卡片缩略到 400px 宽时仍可辨认（**最小可读笔画 ≥ 2 输出像素**）。
- 别名：`github` / `repo` / `social` → `og`；`xiaohongshu` / `red` → `xhs`。

---

## 三、渲染管线（沿用已验证的做法，去掉浏览器依赖）

```
文本 + 样式参数
   ↓  ① 字体解析（内置字体注册表 / --font 指定任意 TTF）
mask = Pillow 渲染 alpha 掩膜（单行、无抗锯齿、裁剪到 bbox）
   ↓  ② 自动适配：二分搜索字号，使 bbox 宽度 ≤ 内容区宽度
   ↓  ③ 掩膜 → 水平游程合并 → 图元 Rect(x, y, w, h)   ← 关键：一切皆整数像素
   ↓  ④ 布局：按 mode 策略计算每块的锚点、间距、投影偏移
图元列表（背景 / 投影层 / 主体层 / 装饰线 / 徽标）
   ↓                       ↓
⑤a Pillow 逐矩形填充    ⑤b SVG 序列化（shape-rendering="crispEdges"）
   ↓                       ↓
   PNG（整数倍放大）        SVG（完全自包含，不依赖字体文件）
```

要点（沿用 `make_pixellogo.py` 里踩过的坑）：

1. **投影层与主体层共用同一份掩膜**，只做偏移，不二次渲染——否则字形会错位。
2. **不用 `<text>`**，全部转 `<rect>`；SVG 因此可在任何环境复现，不受字体 hinting 影响。
3. 所有坐标必须是整数；`--scale` 只做最后一步整数放大，不在中间引入半像素。
4. `--renderer browser` 作为可选后备（追求特定 Chrome 字形观感时），默认 `raster`。

---

## 四、参数清单

### 4.1 内容

| 参数                 | 类型    | 默认  | 说明                                 |
| ------------------ | ----- | --- | ---------------------------------- |
| `--title, -t`      | str   | 必填  | 主标题；`\n` 或重复传参表示多行                |
| `--subtitle, -s`   | str[] | 空   | 副标题，每个值一行                          |
| `--desc, -d`       | str[] | 空   | 底部说明文字，每个值一行                       |
| `--eyebrow, -e`    | str   | 空   | 标题上方的小字分类标签（如 `TOOLKIT / 2026`） |
| `--badge`          | str   | 空   | 右上角方块徽标文字（如 `NEW`、`v1.0`）         |

### 4.2 风格

| 参数                            | 类型            | 默认        | 说明                            |
| ----------------------------- | ------------- | --------- | ----------------------------- |
| `--preset, -p`                | enum          | `terminal` | 见 4.3 预设表                     |
| `--bg` `--primary` `--fg` `--accent` `--shadow-color` | hex | 取 preset | 单色覆盖，允许只改其中一两个                |
| `--shadow-offset`             | int（格）        | `1`       | `0` = 纯扁平无投影，`2` = 强浮雕       |
| `--title-size`                | int           | `auto`    | `auto` 时按内容区宽度二分搜索            |
| `--font-title` `--font-sub` `--font-body` | 内置名 / TTF 路径 | 取 preset | 内置：`press-start-2p` `silkscreen` `pixelify` |
| `--tracking`                  | float         | `1.0`     | 字距倍率（相对 1 个笔画宽）               |
| `--leading`                   | float         | `1.4`     | 行高倍率                          |
| `--uppercase`                 | flag          | off       | 强制大写（Silkscreen 无小写字形时的兜底）   |

### 4.3 风格预设

| preset     | 定位     | 底色        | 主色        | 强调色       | 投影色       |
| ---------- | ------ | --------- | --------- | --------- | --------- |
| `terminal` | 参考原味   | `#EEF1F6` | `#02ADFB` | `#FF6104` | `#2B3444` |
| `cyber`    | 暗夜赛博   | `#0D1117` | `#00E5A0` | `#FF3D81` | `#05070C` |
| `arcade`   | 复古街机   | `#1B1F27` | `#FFD200` | `#FF5F1F` | `#000000` |
| `candy`    | 柔和糖果   | `#FFF5F7` | `#FF7EB6` | `#4ECDC4` | `#8A5A72` |
| `minimal`  | 极简专业   | `#F8FAFC` | `#2563EB` | `#F97316` | `#1E293B` |

每个 preset 同时携带：字体组合、投影偏移、装饰线风格、默认对齐方式。深色 preset 自动切浅色字色。

### 4.4 布局与装饰

| 参数               | 类型             | 默认      | 说明                         |
| ---------------- | -------------- | ------- | -------------------------- |
| `--align`        | `left`\|`center` | `left`  | 全图统一一种对齐                   |
| `--margin`       | float（比例）      | `0.06`  | 安全边距，相对画布短边                |
| `--vertical`     | `top`\|`center`  | 按 mode | 内容块纵向锚定                    |
| `--divider`      | `line`\|`dash`\|`block`\|`none` | `line` | 装饰分隔线样式                    |
| `--divider-width`| float（比例）      | `0.42`  | 占内容区宽度的比例                  |
| `--bg-pattern`   | `none`\|`grid`\|`dots` | `none` | 背景点阵 / 网格（违背"无纹理"约束，默认关闭） |

### 4.5 输出与运行

| 参数                   | 类型                    | 默认             | 说明                          |
| -------------------- | --------------------- | -------------- | --------------------------- |
| `--mode, -m`         | enum                  | `xhs`          | 见第二节                        |
| `--size`             | `WxH`                 | —              | 自定义画布（隐含 `mode=custom`）      |
| `--scale`            | int                   | `2`            | 输出放大倍数                      |
| `--format, -f`       | `png`\|`svg`\|`both`  | `both`         | 输出格式                        |
| `--out, -o`          | path                  | `out/<slug>`   | 单文件路径或目录；`{mode}` `{title}` 占位符 |
| `--config, -c`       | path                  | —              | JSONC 配置文件                  |
| `--set`              | `k=v`（可重复）           | —              | 最高优先级覆盖，支持 `colors.primary=#fff` 点路径 |
| `--dry-run`          | flag                  | off            | 只打印合并后的最终配置，不渲染              |
| `--json`             | flag                  | off            | 机器可读输出（路径、尺寸、耗时）            |
| `--open`             | flag                  | off            | 生成后调用系统默认程序打开               |
| `--list`             | `presets`\|`modes`\|`fonts` | —        | 列清单                         |
| `--strict`           | flag                  | off            | 未知键报错而非警告                   |

---

## 五、配置文件格式（JSONC）

```jsonc
// pixellogo.jsonc —— 注释与尾逗号均被支持
{
  "$schema": "./schema/pixellogo.schema.json",

  "mode": "xhs",            // 小红书 1080×1440
  "preset": "terminal",

  "title": "REA",
  "subtitle": ["REVERSE ENGINEER", "ANYTHING"],
  "desc": ["One CLI + MCP server for agents", "From binaries to websites"],

  "colors": {
    "primary": "#02ADFB",   // 只覆盖需要改的键，其余继承 preset
  },

  "layout": {
    "align": "left",
    "margin": 0.06,
    "divider": "line",
  },

  "output": {
    "dir": "out",
    "formats": ["png", "svg"],
    "scale": 2,
  },
}
```

批量：顶层为数组时，每个元素是一份独立配置，一次生成多张。

```jsonc
[
  { "mode": "xhs", "title": "REA", "subtitle": ["REVERSE ENGINEER"] },
  { "mode": "og",  "title": "REA", "desc": ["Repository social preview"] }
]
```

**优先级**：内置默认 → `preset` → 配置文件 → CLI 参数（含 `--set`）。`--dry-run` 用于确认这四层叠加后的结果。

---

## 六、命令示例

```bash
# 最短用法：默认环境
pixellogo -t "REA" -s "REVERSE ENGINEER" -d "One CLI for agents"

# 三模式一次出图
pixellogo -c pixellogo.jsonc -m xhs -f png -o out/rea-xhs.png
pixellogo -c pixellogo.jsonc -m 4:3 -f png -o out/rea-4x3.png
pixellogo -c pixellogo.jsonc -m og  -f png -o out/rea-og.png

# 临时改一项配色，不动配置文件
pixellogo -c pixellogo.jsonc --set colors.accent=#FF3D81 --open

# 换预设 + 关闭投影
pixellogo -t "DEV" -p cyber --shadow-offset 0 -o out/

# 查看最终合并配置
pixellogo -c pixellogo.jsonc -m og --dry-run

# 批量
pixellogo -c batch.jsonc -o out/ --json
```

---

## 七、代码结构

```
pixellogo/
├─ cli.py                 # argparse 入口、参数 → 配置合并、错误提示
├─ config.py              # JSONC 解析、点路径 --set、四层合并、校验
├─ schema/pixellogo.schema.json
├─ presets.py             # 5 套风格预设（配色 + 字体 + 投影 + 装饰）
├─ modes.py               # 画布规格与各 mode 的布局策略
├─ fonts.py               # 内置字体注册表、路径解析、缺失下载兜底
├─ text.py                # 掩膜渲染、度量、自动断行、字号二分适配
├─ scene.py               # 图元模型：Rect / Divider / Badge / Group
├─ layout.py              # 三种 mode 的排版实现
├─ render/raster.py       # Pillow 后端
├─ render/svg.py          # SVG 后端（共享图元模型）
└─ render/browser.py      # 可选：Chrome/Edge headless 后备

examples/    *.jsonc 可直接运行的示例
tests/       golden image + 配置合并 + CLI 快照
```

---

## 八、实施阶段

| 阶段  | 内容                                                            | 验收标准                                          |
| --- | ------------------------------------------------------------- | --------------------------------------------- |
| M0  | 项目脚手架：`pyproject.toml`、包结构、`pixellogo --version`              | `pipx install .` 后命令可用                         |
| M1  | 渲染核心：掩膜 → 图元 → Pillow PNG / SVG 双后端                          | 用现有 `samples/` 参数复现出与当前 PNG 视觉一致的成品（像素级 diff 为 0） |
| M2  | `modes.py` + `layout.py`：三模式各自排版                              | 三模式各出图一张，缩略到 400px 宽标题仍可读                     |
| M3  | `config.py`：JSONC、四层合并、schema 校验、`--dry-run`                   | 示例配置齐全，非法配置给出定位到行的错误                          |
| M4  | 5 套 preset + 字体注册 + 色板/对比度校验（≤4 色警告）                            | `--list presets` 可用，深色 preset 字色自动反转           |
| M5  | 批量、`--json`、测试、GitHub Actions（每次 push 自动出三模式 demo 图）           | CI 绿，README 内嵌自动生成的示例图                         |
| M6  | 可选：Python API（`from pixellogo import render`）+ MCP server 封装 | 可被 agent 调用，参数与 CLI 同构                         |

---

## 九、风险与前置问题

1. **中文字形缺失（最高优先级）**。现有三款字体（Press Start 2P / Silkscreen / Pixelify Sans）**没有中文字形**，中文标题会渲染成缺字方块。需要引入一款开源中文像素字体（如 Fusion Pixel Font、Zpix），或要求 `--font-title` 指向本地中文像素字体。这一点必须在 M2 之前定，否则整个中文场景不可用。
2. **字体授权**。三款字体均为 SIL OFL，允许再分发，但仓库里目前**没有附带 OFL 许可证文本**，公开仓库应在 `fonts/` 下补齐 `OFL.txt`，否则分发合规性存疑。
3. **浏览器依赖移除**。默认走 Pillow 后，不同 FreeType 版本的字形边缘可能相差 1px；golden image 测试需设容差，或固定 Pillow 版本区间。
4. **OG 图裁切**。GitHub 在部分位置按 2:1 居中裁切，内容需留在中央安全区，不能贴边。
5. **`4:3` 的用途边界**。若目标是幻灯片全屏，16:9 更合适；建议后续增加 `16:9`（1920×1080）作为第四个 mode，成本很低（新增一条画布规格 + 布局参数）。

---

## 十、实施结果与偏差

M0–M6 已落地，实现在 `src/pixellogo/`，测试见 `tests/`。与本文最初的设想相比，有以下偏差：

| 项目 | 计划 | 实际 | 原因 |
| --- | --- | --- | --- |
| 中文像素字体 | 引入 Fusion Pixel 或 Zpix | 选定 **Ark Pixel 12px Proportional (zh_hans)** | OFL 1.1 明确、单一 TTF 覆盖中日韩，5MB 可直接随包分发 |
| 中文标题字重 | 未定 | 命中回退字体时按字号做形态学膨胀加粗 | Ark Pixel 笔画偏细，与 Press Start 2P 落差过大 |
| `og` 文本宽度 | 左侧 62% | **72%** | 72% 下标题更饱满，右下水阶梯仍有余量；`--motif none` 可回到纯文本 |
| `4:3` 纵向 | 顶部锚定 | **居中锚定** | 内容较少的横版顶部锚定会在下半幅留出大片空白 |
| 标题字号 | 只收缩 | **双向自适应** | 短标题在宽画布上会显小，改为收缩后再放大到接近撑满 |
| 默认输出格式 | — | **both** | 需求要求可选格式，默认两种都出，`-f png` 可只出位图 |

风险项处理情况：

1. 中文字形缺失 —— 已通过 Ark Pixel + 整行统一字形解决；
2. 字体的 OFL 许可文本 —— 已补齐四份原文，仓库本体采用 MIT；
3. 浏览器依赖 —— 已改为 Pillow 直出，`render/browser.py` 未实现，也不需要；
4. OG 裁切安全区 —— 内容全部落在 `margin` 内，未贴边；
5. `16:9` 模式 —— 仍未实现，`--size 1920x1080` 可临时替代。

## 十一、后续可做

- 增加 `16:9`（1920×1080）与 `1:1`（1080×1080）两个常用画布；
- 输出 Python API（`from pixellogo import render`）与 MCP server，供 agent 直接调用；
- 背景点阵 / 扫描线纹理（`--bg-pattern`），当前为保持"无纹理"不变式未开放；
- 多语言字体包（`zh_hant` / `ja` / `ko`）按需下载，而非全部随包。
