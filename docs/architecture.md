# 项目文件架构

本文回答三个问题：仓库里有哪些东西、每一部分负责什么、这些结构决定了哪些能力边界。
文件树只展开三层；第四层（`render/`、`assets/fonts/`、`assets/licenses/`、`docs/images/gallery/` 的内部）
在行内注释里说明，避免树状图噪音过大。

命令行的逐参数说明、实测容量与限制数据见 [`cli-guide.md`](cli-guide.md)。

---

## 一、项目速览

| 项 | 值 |
| --- | --- |
| 包名 / 命令 | `pixellogo`（`pyproject.toml` 的 `name` 与 `cli.PROG` 一致） |
| 版本 | `0.3.0` |
| Python | `>=3.9` |
| 运行时依赖 | 仅 `pillow>=9.0`（开发依赖 `pytest>=7.0`，实际测试用标准库 `unittest`） |
| 入口 | `pixellogo = "pixellogo.cli:main"`，另支持 `python -m pixellogo` |
| 布局 | setuptools `src` 布局，`package-dir = {"" = "src"}` |
| 代码规模 | 18 个 `.py` 模块，约 3,270 行 |
| 测试 | 8 个文件、146 个用例 |
| 许可 | 代码 MIT；随包字体 SIL OFL 1.1 |
| 定位 | 把标题 / 副标题 / 说明文字渲染成 8-bit 复古终端风格像素图，输出 PNG + SVG |

一句话概括架构：**文字 → 二值 alpha 掩膜 → 按行水平游程 → 整数坐标矩形 `Rect` → 同一份 `Scene` 交给 PNG / SVG 两个后端**。
两种格式共用一套几何数据，所以像素级一致；全程不引入抗锯齿、渐变与半透明。

---

## 二、文件树

```
E:/像素风格工具包/
├─ pyproject.toml                  # 打包元数据 + console_scripts 入口 + 包内数据白名单
├─ README.md                       # 英文主文档（默认入口）
├─ README.zh-CN.md                 # 简体中文版，与英文逐节镜像
├─ LICENSE                         # MIT 许可；字体许可见 assets/licenses/
├─ .gitattributes                  # 统一 LF 换行；png / ttf / woff 标记为二进制
├─ .gitignore                      # 忽略 build/ dist/ out/ __pycache__/ 等产物
│
├─ .github/
│  └─ workflows/
│     └─ tests.yml                 # CI：Python 3.9–3.12 四版本矩阵跑 unittest，另有出图作业
│
├─ docs/                           # 文档与配图
│  ├─ architecture.md              # 本文：文件架构、分层与架构级限制
│  ├─ cli-guide.md                 # 命令行完整手册：由浅入深，含能力边界与实测容量
│  ├─ design.md                    # 早期设计与 M0–M6 里程碑记录（部分描述已被实现超越）
│  ├─ style-spec.md                # 风格规格：不变式清单、提示词模板、配色速查
│  ├─ gallery.md                   # 命令示例画廊：40 张成品 + 逐条命令（当前仅中文）
│  └─ images/                      # 配图目录，共 59 张 PNG
│     ├─ banner.png                # README 首图
│     ├─ poster.png / card.png / slide.png / square.png   # 画布示意图
│     ├─ lang-ja.png               # 日文字形示例
│     ├─ pattern-*.png             # 三种背景纹理：grid / dots / scanlines
│     ├─ preset-*.png              # 十套预设缩略图（terminal … paper）
│     └─ gallery/                  # 画廊成品图 40 张（python.png、zig.png …）
│
├─ examples/                       # 可直接运行的 JSONC 配置
│  ├─ rea.jsonc                    # 单张：poster + terminal，居中排版
│  ├─ og.jsonc                     # 单张：banner + cyber，中文标题 + 徽标 + 阶梯装饰
│  └─ batch.jsonc                  # 批量：顶层数组 3 项（poster / card / banner）
│
├─ src/
│  ├─ pixellogo.egg-info/          # editable 安装生成的元数据（可再生，不要手改）
│  └─ pixellogo/                   # 包本体：18 个 .py，约 3,270 行
│     ├─ __init__.py               # 版本号与对外导出；缺 Pillow 时抛带安装提示的 ImportError
│     ├─ __main__.py               # python -m pixellogo 的入口，转调 cli.main
│     ├─ cli.py                    # argparse 参数表、fonts 子命令、--list、退出码
│     ├─ config.py                 # 四层配置合并、校验、Settings 与 --dry-run 快照
│     ├─ i18n.py                   # 中英文案表、locale 探测、argparse 报错本地化
│     ├─ jsonc.py                  # 自写 JSONC 解析（// 与 /* */ 注释、尾逗号）
│     ├─ modes.py                  # 五种画布规格、比例别名、custom_mode（--size）
│     ├─ presets.py               # 十套配色预设与 WCAG 对比度计算
│     ├─ fonts.py                  # 字体注册、TTF cmap 解析、字形覆盖检测与整行挑字
│     ├─ fontpack.py               # 中日韩字形变体按需下载（urllib + zipfile）
│     ├─ layout.py                 # 行栈排版引擎：Design → Scene，含折行与缩字号回退、投影 / 分隔线 / 纹理 / 缺字告警
│     ├─ text.py                   # 文字度量与折行、二值掩膜 → 整数矩形（THRESHOLD = 128）
│     ├─ scene.py                  # Rect / Scene 图元模型
│     ├─ paths.py                  # 文件名 slugify（截断 60 字符）、输出路径、批量去重
│     ├─ api.py                    # Python API：render / render_many / make_scene / make_image / to_svg_text
│     ├─ render/                   # 两个后端（第四层）：__init__.py 按扩展名分派并写盘，
│     │                            #   raster.py 用 Pillow 逐矩形填充，svg.py 序列化 <rect> + crispEdges
│     ├─ schema/                   # pixellogo.schema.json（draft-07）：仅覆盖部分键，枚举落后于代码
│     └─ assets/                   # 包内资源（第四层）：
│                                  #   fonts/ 四款 TTF —— ArkPixel-zh-hans、PressStart2P、
│                                  #     Silkscreen、PixelifySans；
│                                  #   licenses/ 五份 OFL 原文（含未随包的 Galmuri）
│
├─ tests/                          # 8 个文件、160 个用例，标准库 unittest
│  ├─ test_cli.py                  # 以子进程跑 CLI：version / help / list / 尺寸 / 格式 / 批量 / 错误码
│  ├─ test_config.py               # JSONC、deep_merge、set_path、类型转换、示例配置、wrap 开关
│  ├─ test_i18n.py                 # 语言探测、中英键一致性、argparse 报错翻译、列宽
│  ├─ test_layout.py               # 标题自适应、投影、分隔线、徽标、motif、纹理、缺字告警、折行与溢出
│  ├─ test_fonts.py                # 字体注册、cmap 覆盖、整行挑字、变体下载逻辑
│  ├─ test_render.py               # PNG / SVG 一致性、scale、crispEdges、宽度度量与折行
│  ├─ test_presets.py              # 预设色板与对比度下限
│  └─ test_api.py                  # Python API 五个函数
│
├─ build/                          # 构建中间产物（gitignore，可整目录删除）
│  ├─ bdist.win-amd64/             # 空目录
│  └─ lib/pixellogo/               # 源码快照副本，可能滞后于 src/，勿当作源码参考
│
└─ dist/                           # 发布产物（gitignore）
   ├─ pixellogo-0.3.0-py3-none-any.whl    # wheel
   ├─ pixellogo-0.3.0.tar.gz              # sdist
   └─ pixellogo-0.3.0-portable.zip        # 便携包：包 + pixellogo.cmd / .sh + RUNNING.txt + 双 README
```

**可再生 vs 受版本控制**：`build/`、`dist/`、`src/pixellogo.egg-info/`、各级 `__pycache__/` 都是产物，可以删除后重建；
其余文件都是源码或素材，改动需提交。`build/lib/pixellogo/` 只是 `src/` 的**快照副本**，可能滞后于源码，
读代码请只看 `src/pixellogo/`；打包前务必先删掉 `build/`，否则旧的快照文件会被一起打进 wheel
（v0.2.0 的 wheel 就因此多带了一个已废弃的 `ArkPixel12pxProportional.ttf`，v0.3.0 起在干净构建下修正）。

---

## 三、分层与模块职责

自上而下六层，依赖只允许向下：

| 层 | 模块 | 职责 | 关键点 |
| --- | --- | --- | --- |
| 入口层 | `cli.py`（318 行）、`__main__.py` | 解析命令行、判定子命令、组织一次运行 | 建 parser 前先预扫 `--ui-lang`，保证 `--help` 也按指定语言排版；`argparse` 报错被覆写为本地化文案并统一 `exit(2)`；排版阶段产生的诊断（缺字、溢出）在这里打到 stderr |
| 配置层 | `config.py`（448 行）、`jsonc.py`（107 行）、`i18n.py`（572 行） | 四层合并、枚举 / 范围校验、生成 `Design` 与 `Settings` | 合并顺序 `默认 < preset < 配置文件 < 命令行`；`deep_merge` 对列表整体替换、跳过 `None`；未知键只告警；`_as_bool` 让 `"false"` 这类字符串也按关闭处理；缺字告警在这里并入 `Settings.warnings` |
| 语义层 | `modes.py`（161 行）、`presets.py`（210 行）、`fonts.py`（337 行）、`fontpack.py`（89 行） | 画布规格、配色预设、字体注册与字形覆盖、变体下载 | 画布尺寸是**逻辑像素**，输出乘 `scale`；预设自带字体配对与投影强度；`cmap` 用标准库 `struct` 自行解析，不依赖 Pillow 的缺字行为 |
| 排版层 | `layout.py`（475 行）、`text.py`（263 行）、`scene.py`（50 行）、`paths.py`（39 行） | 文字度量与折行、成膜、行栈堆叠、溢出回退、装饰绘制、落盘路径 | `THRESHOLD = 128` 二值化；`MOTIF_RESERVE = 0.26` 为右侧装饰让位；`MIN_TEXT_SIZE = 9` 是缩字号下限；标题双向自适应，上限约画布高 42%；投影由矩形派生，不重绘 |
| 渲染层 | `render/__init__.py`（38 行）、`raster.py`（18 行）、`svg.py`（28 行） | 按扩展名分派后端并写盘 | PNG 逐矩形填充后整体按整数倍放大；SVG 是一串 `<rect>`，`shape-rendering="crispEdges"`，不依赖字体文件 |
| 对外 API | `api.py`（80 行） | 关键字参数与 JSONC 键一一对应 | `render` 写文件、`make_image` 只出图、`make_scene` 只出几何、`to_svg_text` 只出源码 |

---

## 四、数据流

```
用户输入（CLI / JSONC / Python 关键字参数）
        │
        ▼
  config.resolve() ── deep_merge ── validate ──► Design + Settings（scale / out / formats / warnings）
        │
        ├─ --dry-run ──► Settings.describe() 以 JSON 打印，不渲染、不写盘
        │
        ▼
  layout.build_scene(Design)
        │   ├─ 取配色（预设 + 单色覆盖）
        │   ├─ 画背景纹理（grid / dots / scanlines，纯色矩形）
        │   ├─ 副标题 / 说明 / 小字标签按文本区宽度折行（text.measure_width + text.wrap_line）
        │   ├─ 每行文字 → text.line_mask()：整行选定唯一字体 → 画进灰度画布 → 阈值二值化 → 裁边
        │   ├─ 行栈堆叠（标题自适应字号 → 副标题 → 分隔线 → 说明），按 vertical 垂直定位
        │   ├─ 总高超过可用高度时按比例缩字号、重新折行重排，缩到 9px 仍超出则记录诊断
        │   ├─ text.mask_rects()：逐行取水平游程，上下完全相同的游程合并成整块矩形
        │   └─ 标题投影由矩形整体偏移派生（不改字形），再叠加徽标与阶梯装饰
        ▼
     Scene（width / height / background + Rect 列表）
        │
        ├─ render.svg  → 字符串：<svg> + 若干 <rect>
        └─ render.raster → Pillow 图像：逐矩形填充，再按 scale 整数倍放大
        ▼
  paths.targets() 决定文件名 → paths.unique_paths() 批量去重 → 写盘 → 打印路径与尺寸（或 --json）
```

由此可以解释两个可观测行为：SVG 与 PNG 永远像素级对齐（同一批矩形）；放大后边缘仍是整块方块（没有插值重采样）。

---

## 五、架构决定的固有限制

这一节只讲「为什么会有这些限制」，量化数据与规避方法见 [`cli-guide.md` 的能力边界与限制](cli-guide.md#九能力边界与限制)。

1. **只支持纯色背景**。`Scene` 只有 `background` 一个纯色字段，所有绘制都是不透明矩形；没有图层、透明度与混色模型，因此无法贴图片背景、无法做渐变与半透明。`--bg-pattern` 只是用纯色矩形拼出纹理。
2. **没有抗锯齿，因此坐标必须是整数**。掩膜按 128 阈值二值化后转成整数矩形，任何非整数缩放都会破坏「每条边都是方块」的不变式，所以 `--scale` 只接受 1–8 的整数倍，旋转、斜切、描边都没有实现路径。
3. **单行统一字体**。`pick_unified()` 为整行只选一款字体，目的是避免同一行出现两种笔画粗细；代价是一行里无法混用拉丁与中文字形，且当某款字体缺个别字形时，那一行只能退而求其次（取缺字最少的字体），缺的字仍会渲染成方块——不会回落到系统字体。
4. **单进程、纯 CPU、同步执行**。渲染是顺序的 Python 循环，没有多线程 / 多进程 / GPU 分支；批量配置逐项串行处理。单张图在毫秒到百毫秒量级，但不适合一次出上千张。
5. **没有插件与主题扩展机制**。预设、画布、字体都是模块内的字面量表（`MODES`、`PRESETS`、`BUILTIN_FONTS`），要加新预设只能改源码并重新安装，不能通过配置目录热加载。
6. **schema 与代码不同步**。`schema/pixellogo.schema.json` 只覆盖部分键，`mode` / `preset` 枚举落后于当前实现，编辑器按它补全会误报——它是便利件，不是校验源；真正的校验在 `config.py`。
7. **配置是「层层覆盖」而不是「可回退」**。命令行只能向上覆盖，`auto` 会被过滤、空字符串会被丢弃；布尔开关里只有折行做成了成对的 `--wrap/--no-wrap`，`--uppercase` 仍是单向开关，打开后无法用命令行改回关闭。
8. **文本的自适应是有下限的**。副标题、说明与小字标签会按文本区宽度折行，总高放不下时再按比例缩小字号（下限 9px）；但折行不会切断单词（除非单个词本身超宽，此时按字符硬切），标题也不参与折行，缩到下限仍放不下时就只剩「告警 + 被画布裁切」这一条路。容量上限见 [`cli-guide.md` 第九节](cli-guide.md#九能力边界与限制)。

---

## 六、扩展指引

| 想做的事 | 需要改的文件 |
| --- | --- |
| 加一套配色预设 | `src/pixellogo/presets.py` 的 `PRESETS`；同步 README 预设表与 `docs/images/preset-*.png`；`--list presets` 会自动带上 |
| 加一种画布 | `src/pixellogo/modes.py` 的 `MODES`（宽高、`text_ratio`、`title_ratio`、默认对齐与 motif）+ `ALIASES`；在 `i18n.py` 补 `mode.<key>` 文案，否则 `--list modes` 回退英文 |
| 换或加内置字体 | 字体文件放 `src/pixellogo/assets/fonts/`，许可证放 `assets/licenses/`，在 `fonts.py` 的 `BUILTIN_FONTS` 登记；`pyproject.toml` 的 `package-data` 已按通配符包含 |
| 加一个命令行参数 | `cli.py` 的 `build_parser()` 加参数 → `config.py` 的 `cli_to_config()` 映射到配置键 → 在 `TOP_KEYS` / `LAYOUT_KEYS` 登记 → `config.resolve()` 校验 → `layout.py` 消费；缺一处在 `--dry-run` 里看不到 |
| 加一条用户可见文案 | `src/pixellogo/i18n.py` 的 en 与 zh 两张表**同键**添加，`tests/test_i18n.py` 会校验键一致性 |
| 新增测试 | `tests/` 下按模块建 `test_*.py`，用标准库 `unittest`；CI 命令为 `python -m unittest discover -s tests -v` |

---

## 七、相关文档

- [`cli-guide.md`](cli-guide.md) —— 命令行完整手册：由浅入深的用法、参数速查、配置与脚本化、能力边界与限制、排错手册。
- [`gallery.md`](gallery.md) —— 40 张成品与逐条命令。
- [`style-spec.md`](style-spec.md) —— 风格不变式与提示词库。
- [`design.md`](design.md) —— 早期设计记录，含当时的取舍与里程碑（部分已被实现超越，仅作历史参考）。
