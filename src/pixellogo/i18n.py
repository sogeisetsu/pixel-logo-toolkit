"""命令行输出语言：中英双语，自动跟随终端语言，也可显式指定。

语言解析顺序（前者优先）：

1. ``--ui-lang auto|en|zh``（命令行参数）
2. 环境变量 ``PIXELLOGO_UI_LANG``
3. 终端 locale：``LC_ALL`` → ``LC_MESSAGES`` → ``LANG`` → ``LANGUAGE``
4. Windows 系统界面语言（``GetUserDefaultUILanguage``）
5. 兜底：英语

只有 ``en`` 与 ``zh`` 两套文案；``en-US``、``zh-CN``、``zh_TW`` 等写法都接受。
缺少某个键时回退到英语，再回退到键名本身，避免出现空字符串。
"""
from __future__ import annotations

import os
import re

SUPPORTED = ("en", "zh")
DEFAULT = "en"
ENV_VAR = "PIXELLOGO_UI_LANG"

#: 各类 locale 写法到内部语言代码的映射
ALIASES = {
    "en": "en",
    "en-us": "en",
    "en_us": "en",
    "en-gb": "en",
    "english": "en",
    "zh": "zh",
    "cn": "zh",
    "chinese": "zh",
    "zh-cn": "zh",
    "zh_cn": "zh",
    "zh-hans": "zh",
    "zh-sg": "zh",
    "zh-hans-cn": "zh",
    "zh-hant": "zh",
    "zh-tw": "zh",
    "zh-hk": "zh",
    "zh-hant-tw": "zh",
}

_cached: str | None = None


def normalize(value: str | None) -> str | None:
    """把各种语言写法规范成 ``en`` / ``zh``；无法识别时返回 ``None``。"""
    if not value:
        return None
    key = value.strip().lower().replace(" ", "")
    if key in ALIASES:
        return ALIASES[key]
    head = re.split(r"[._@\-]", key, maxsplit=1)[0]
    return ALIASES.get(head)


def _locale_prefix(value: str) -> str | None:
    """从 ``zh_CN.UTF-8`` 这类 locale 值里取出语言部分。"""
    if not value:
        return None
    first = value.split(":", 1)[0].strip()
    if not first:
        return None
    # LANG=C / C.UTF-8 / POSIX 都表示「无本地化」，按英语处理
    base = first.split("@", 1)[0].split(".", 1)[0].strip()
    if base.upper() in ("C", "POSIX"):
        return "en"
    return normalize(first)


def _windows_ui_language() -> str | None:
    """Windows 上没有 locale 环境变量时的兜底：系统界面语言。"""
    if os.name != "nt":
        return None
    try:
        import ctypes

        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - 仅 Windows 生效
        return None
    primary = langid & 0x3FF
    if primary == 0:
        return None
    return "zh" if primary == 0x04 else "en"


def detect() -> str:
    """按约定顺序推断语言，返回 ``en`` 或 ``zh``。"""
    explicit = os.environ.get(ENV_VAR, "").strip()
    if explicit and explicit.lower() not in ("auto", ""):
        code = normalize(explicit)
        if code:
            return code
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        code = _locale_prefix(os.environ.get(name, ""))
        if code:
            return code
    return _windows_ui_language() or DEFAULT


def set_language(value: str | None = None) -> str:
    """显式设定语言；``None`` 或 ``auto`` 表示重新按环境推断。"""
    global _cached
    if value is None or value.strip().lower() in ("", "auto"):
        _cached = detect()
        return _cached
    code = normalize(value)
    if code is None:
        raise ValueError(
            f"unsupported ui language {value!r}; choose from: auto, en, zh"
        )
    _cached = code
    return _cached


def get_language() -> str:
    """当前输出语言（首次调用时推断并缓存）。"""
    if _cached is None:
        return set_language("auto")
    return _cached


def reset() -> None:
    """清除缓存的语言，下一次 ``get_language()`` 重新推断（供测试使用）。"""
    global _cached
    _cached = None


def is_chinese() -> bool:
    return get_language() == "zh"


def join(items) -> str:
    """列表连接符：中文用顿号，英文用逗号。"""
    return ("、" if is_chinese() else ", ").join(str(item) for item in items)


def display_width(text: str) -> int:
    """终端显示宽度：东亚宽字符按 2 列计。"""
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)


def pad(text: str, width: int) -> str:
    """按显示宽度左对齐补空格，避免中英混排时列错位。"""
    return text + " " * max(0, width - display_width(text))


MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # ---- 帮助页 ----
        "cli.description": "Render 8-bit / retro-terminal pixel art (PNG / SVG).",
        "cli.epilog": """\
Common examples
  Minimal
    pixellogo -t "REA" -s "REVERSE ENGINEER" -d "One CLI for agents"

  Canvas and format
    pixellogo -t "REA" -m poster -f png -o out/
    pixellogo -t "REA" -m banner -f svg -o out/banner.svg

  Style and palette
    pixellogo -t "PIXEL" -p cyber
    pixellogo -t "PIXEL" -p forest --set colors.accent=#FF3D81

  CJK title
    pixellogo -t "像素工具包" -s "PIXEL LOGO TOOLKIT" --badge NEW

  Config file
    pixellogo -c examples/rea.jsonc
    pixellogo -c examples/batch.jsonc -o out/ --json

  Glyph variants
    pixellogo fonts                    list font status for every language
    pixellogo fonts install ja         download the Japanese font on demand
    pixellogo -t "タイトル" --lang ja

  Inspect options
    pixellogo --list modes
    pixellogo --list presets
    pixellogo --list fonts

Output language: --ui-lang auto|en|zh, or the PIXELLOGO_UI_LANG environment variable
Priority: built-in defaults < --preset < config file < command line
Docs: https://github.com/sogeisetsu/pixel-logo-toolkit
""",
        "cli.group.general": "General options",
        "cli.group.content": "Content",
        "cli.group.style": "Style",
        "cli.group.layout": "Layout",
        "cli.group.output": "Output",
        "cli.group.config": "Config",
        "cli.group.misc": "Misc",
        "cli.arg.help": "show this help and exit",
        "cli.arg.version": "show the version and exit",
        "cli.arg.title": "main title; \\n starts a new line",
        "cli.arg.subtitle": "subtitle line; repeatable",
        "cli.arg.desc": "footer note line; repeatable",
        "cli.arg.eyebrow": "small label above the title",
        "cli.arg.badge": "badge text in the top-right corner",
        "cli.arg.preset": "style preset, see --list presets (default: terminal)",
        "cli.arg.bg": "background color",
        "cli.arg.fg": "text color",
        "cli.arg.primary": "primary color (title)",
        "cli.arg.accent": "accent color (divider / badge)",
        "cli.arg.shadow_color": "shadow color",
        "cli.arg.shadow_offset": "shadow depth in blocks, 0 disables (default: 1)",
        "cli.arg.title_size": "title size in pixels; auto-fits the canvas by default",
        "cli.arg.tracking": "letter-spacing multiplier; 1.0 is the natural advance",
        "cli.arg.leading": "line-height multiplier (default: 1.0)",
        "cli.arg.uppercase": "render all text in uppercase",
        "cli.arg.lang": "CJK glyph variant: zh-hans / zh-hant / ja / ko (default: zh-hans)",
        "cli.arg.font_title": "title font",
        "cli.arg.font_sub": "subtitle font",
        "cli.arg.font_body": "body font",
        "cli.arg.align": "horizontal alignment",
        "cli.arg.vertical": "vertical anchoring",
        "cli.arg.margin": "safe margin against the short edge (default: 0.06)",
        "cli.arg.divider": "divider style",
        "cli.arg.divider_width": "divider width ratio (default: 0.42)",
        "cli.arg.motif": "decorative motif",
        "cli.arg.bg_pattern": "background pattern (default: none)",
        "cli.arg.mode": "canvas mode: poster / card / banner / slide / square (default: poster)",
        "cli.arg.size": "custom canvas, e.g. 1200x900",
        "cli.arg.scale": "output upscale factor (default: 2)",
        "cli.arg.format": "output format: png / svg / both (default: both)",
        "cli.arg.out": "output file or directory (default: out/)",
        "cli.arg.config": "JSONC config file",
        "cli.arg.set": "override by dot path, e.g. colors.primary=#FF3D81; repeatable",
        "cli.arg.dry_run": "print the merged config without rendering",
        "cli.arg.json": "emit JSON results for scripting",
        "cli.arg.open": "open the first rendered image",
        "cli.arg.list": "list available options and exit",
        "cli.arg.ui_lang": "output language: auto / en / zh (default: auto, follows the terminal locale)",
        # ---- 错误与提示 ----
        "cli.error": "{prog}: error: {message}",
        "error.pillow": ("pixellogo needs Pillow to render images. "
                         'Install it with: pip install "pillow>=9.0"'),
        "cli.hint.help": "Run {prog} --help for full usage.",
        "cli.warning": "{prog}: warning: {message}",
        # ---- fonts 子命令 ----
        "fonts.status.bundled": "bundled",
        "fonts.status.installed": "downloaded",
        "fonts.status.missing": "not installed",
        "fonts.dir": "Font directory: {path}",
        "fonts.hint": "Install on demand: pixellogo fonts install <zh-hant|ja|ko>",
        "fonts.need_lang": "{prog} fonts install needs a language, e.g. {prog} fonts install ja",
        "fonts.usage": "{prog} fonts supports: list / install <lang>",
        # ---- list ----
        "list.modes": "{key:<8} {ratio:>5}  {label} output {w}×{h}",
        "list.presets": ("{key:<10} {label} bg {bg} primary {primary} "
                         "accent {accent} contrast {ratio:>4.1f}"),
        "list.fonts": "{key:<16} {label:<42} {coverage}",
        # ---- 画布模式 ----
        "mode.poster": "Portrait poster (Xiaohongshu cover)",
        "mode.card": "Landscape card (article header / slides)",
        "mode.banner": "Repository banner (GitHub preview)",
        "mode.slide": "Widescreen slide (16:9)",
        "mode.square": "Square image (social avatar / grid)",
        "mode.custom": "Custom {w}×{h}",
        "mode.unknown": "unknown canvas mode {key!r}; available: {known}",
        "mode.too_small": "custom canvas width and height must be ≥ 64",
        # ---- 风格预设 ----
        "preset.terminal": "Retro terminal (classic)",
        "preset.cyber": "Neon cyber",
        "preset.arcade": "Retro arcade",
        "preset.candy": "Soft candy",
        "preset.minimal": "Clean minimal",
        "preset.noir": "Monochrome documentary",
        "preset.forest": "Forest moss",
        "preset.sunset": "Dusk sunset",
        "preset.ocean": "Deep ocean",
        "preset.paper": "Paper journal",
        "preset.unknown": "unknown style preset {key!r}; available: {known}",
        # ---- 配置校验 ----
        "config.set.missing_key": "--set needs a key",
        "config.lines.item": "every item of {key} must be a string",
        "config.lines.type": "{key} must be a string or an array of strings",
        "config.color.invalid": "color {key}={value!r} is not a valid hex value (e.g. #02ADFB)",
        "config.size.invalid": "canvas size {size!r} is malformed; expected e.g. 1200x900",
        "config.format.type": "format must be png / svg / both, or an array of them",
        "config.format.unknown": "format must be png / svg / both, got {item!r}",
        "config.root.type": "the config root must be an object (top-level array means batch mode)",
        "config.title.missing": "missing title: pass -t/--title or set \"title\" in the config",
        "config.fonts.value": "fonts.{key} must be a font name or a .ttf path",
        "config.enum": "{name} must be one of: {values}",
        "config.range": "{name} must be between {low} and {high}",
        "config.font.missing": "{lang} font is not installed; run `pixellogo fonts install {lang}` first",
        "config.batch.empty": "the config file is an empty array; nothing to render",
        "config.warn.unknown": "unknown config key {key!r} ignored",
        "config.warn.color": "unknown color colors.{key} ignored",
        "config.warn.font": "unknown font fonts.{key} ignored",
        "config.warn.layout": "unknown layout option layout.{key} ignored",
        # ---- 字体 ----
        "font.lang.unknown": "unknown language {lang!r}; available: {known}",
        "font.not_installed": ("{key} font is not installed. Run `pixellogo fonts install {key}` "
                               "and retry, or use --lang zh-hans"),
        "font.name.empty": "font name is empty",
        "font.bundled.missing": "bundled font is missing: {path}",
        "font.unknown": "unknown font {name!r}; built-in fonts: {known}; or pass a .ttf path",
        "font.file.invalid": "not a valid font file",
        "font.file.type": "not a valid TrueType/OpenType font",
        "font.cmap.missing": "font has no cmap table: {path}",
        "font.cmap.unicode": "font has no usable Unicode cmap subtable: {path}",
        # ---- 字体包下载 ----
        "pack.exists": "{key} font already present: {path}",
        "pack.downloading": "Downloading the {key} font pack ({label})…\n  {url}",
        "pack.download.failed": ("download failed: {error}\n"
                                 "Set PIXELLOGO_FONT_MIRROR to a mirror directory and retry."),
        "pack.member.missing": "{member} is not present in the font archive",
        "pack.zip.invalid": "the downloaded file is not a valid zip; a proxy may have intercepted it",
        "pack.file.small": "the font file looks broken (too small); it was removed, please retry",
        "pack.installed": "Installed: {path}",
        # ---- 排版与输出 ----
        "layout.title.empty": "title must not be empty",
        "render.format.unsupported": "unsupported output format {fmt!r}; choose from: {opts}",
        "render.format.suffix": "cannot infer the format from the extension: {name}",
        # ---- JSONC ----
        "jsonc.comment.unclosed": "unclosed block comment: missing */",
        "jsonc.parse.failed": "config parse error (line {line}, column {col}): {msg}",
        "jsonc.file.missing": "config file not found: {path}",
    },
    "zh": {
        # ---- 帮助页 ----
        "cli.description": "生成 8-bit / 复古终端风格的像素图（PNG / SVG）。",
        "cli.epilog": """\
常用示例
  最小用法
    pixellogo -t "REA" -s "REVERSE ENGINEER" -d "One CLI for agents"

  指定画布与格式
    pixellogo -t "REA" -m poster -f png -o out/
    pixellogo -t "REA" -m banner -f svg -o out/banner.svg

  换风格与配色
    pixellogo -t "PIXEL" -p cyber
    pixellogo -t "PIXEL" -p forest --set colors.accent=#FF3D81

  中文标题
    pixellogo -t "像素工具包" -s "PIXEL LOGO TOOLKIT" --badge NEW

  用配置文件
    pixellogo -c examples/rea.jsonc
    pixellogo -c examples/batch.jsonc -o out/ --json

  中文字形变体
    pixellogo fonts                    列出各语言字体状态
    pixellogo fonts install ja         按需下载日文字体
    pixellogo -t "タイトル" --lang ja

  查看选项清单
    pixellogo --list modes
    pixellogo --list presets
    pixellogo --list fonts

输出语言：--ui-lang auto|en|zh，或环境变量 PIXELLOGO_UI_LANG
参数优先级：内置默认 < --preset < 配置文件 < 命令行参数
完整文档：https://github.com/sogeisetsu/pixel-logo-toolkit
""",
        "cli.group.general": "通用选项",
        "cli.group.content": "内容",
        "cli.group.style": "风格",
        "cli.group.layout": "排版",
        "cli.group.output": "输出",
        "cli.group.config": "配置",
        "cli.group.misc": "其他",
        "cli.arg.help": "显示本帮助并退出",
        "cli.arg.version": "显示版本号并退出",
        "cli.arg.title": "主标题，支持 \\n 换行",
        "cli.arg.subtitle": "副标题行，可重复",
        "cli.arg.desc": "底部说明行，可重复",
        "cli.arg.eyebrow": "标题上方的小字标签",
        "cli.arg.badge": "右上角徽标文字",
        "cli.arg.preset": "风格预设，见 --list presets（默认 terminal）",
        "cli.arg.bg": "底色",
        "cli.arg.fg": "字色",
        "cli.arg.primary": "主色（标题）",
        "cli.arg.accent": "强调色（分隔线/徽标）",
        "cli.arg.shadow_color": "投影色",
        "cli.arg.shadow_offset": "投影格数，0 关闭（默认 1）",
        "cli.arg.title_size": "标题字号，缺省按画布自动适配",
        "cli.arg.tracking": "字距倍率，1.0 为字体原始步进，越小越紧凑",
        "cli.arg.leading": "行高倍率，默认 1.0",
        "cli.arg.uppercase": "全部文字转大写",
        "cli.arg.lang": "中日韩字形变体：zh-hans / zh-hant / ja / ko（默认 zh-hans）",
        "cli.arg.font_title": "主标题字体",
        "cli.arg.font_sub": "副标题字体",
        "cli.arg.font_body": "说明文字字体",
        "cli.arg.align": "对齐方式",
        "cli.arg.vertical": "纵向锚定",
        "cli.arg.margin": "安全边距，相对画布短边（默认 0.06）",
        "cli.arg.divider": "分隔线样式",
        "cli.arg.divider_width": "分隔线宽度比（默认 0.42）",
        "cli.arg.motif": "装饰图形",
        "cli.arg.bg_pattern": "背景纹理（默认 none）",
        "cli.arg.mode": "画布模式：poster / card / banner / slide / square（默认 poster）",
        "cli.arg.size": "自定义画布，如 1200x900",
        "cli.arg.scale": "输出放大倍数（默认 2）",
        "cli.arg.format": "输出格式：png / svg / both（默认 both）",
        "cli.arg.out": "输出文件或目录（默认 out/）",
        "cli.arg.config": "JSONC 配置文件",
        "cli.arg.set": "按点路径覆盖配置，如 colors.primary=#FF3D81，可重复",
        "cli.arg.dry_run": "只打印合并后的配置，不渲染",
        "cli.arg.json": "以 JSON 输出结果，便于脚本消费",
        "cli.arg.open": "生成后打开第一张图",
        "cli.arg.list": "列出可选项后退出",
        "cli.arg.ui_lang": "输出语言：auto / en / zh（默认 auto，跟随终端语言）",
        # ---- 错误与提示 ----
        "cli.error": "{prog}: 错误：{message}",
        "error.pillow": ('渲染需要 Pillow，请先安装：pip install "pillow>=9.0"'),
        "cli.hint.help": "用 {prog} --help 查看完整用法。",
        "cli.warning": "{prog}: 提示：{message}",
        # ---- fonts 子命令 ----
        "fonts.status.bundled": "随包内置",
        "fonts.status.installed": "已下载",
        "fonts.status.missing": "未安装",
        "fonts.dir": "字体目录：{path}",
        "fonts.hint": "按需安装：pixellogo fonts install <zh-hant|ja|ko>",
        "fonts.need_lang": "{prog} fonts install 需要语言参数，如：{prog} fonts install ja",
        "fonts.usage": "{prog} fonts 支持：list / install <lang>",
        # ---- list ----
        "list.modes": "{key:<8} {ratio:>5}  {label} 输出 {w}×{h}",
        "list.presets": ("{key:<10} {label} 底 {bg} 主 {primary} "
                         "强调 {accent} 对比度 {ratio:>4.1f}"),
        "list.fonts": "{key:<16} {label:<42} {coverage}",
        # ---- 画布模式 ----
        "mode.poster": "竖版海报（小红书封面）",
        "mode.card": "横版卡片（文章头图 / PPT）",
        "mode.banner": "仓库横幅（GitHub 预览图）",
        "mode.slide": "宽屏幻灯片（16:9）",
        "mode.square": "方形图片（社交头像 / 九宫格）",
        "mode.custom": "自定义 {w}×{h}",
        "mode.unknown": "未知画布模式 {key!r}；可用：{known}",
        "mode.too_small": "自定义画布宽高都必须 ≥ 64",
        # ---- 风格预设 ----
        "preset.terminal": "复古终端（参考原味）",
        "preset.cyber": "暗夜赛博",
        "preset.arcade": "复古街机",
        "preset.candy": "柔和糖果",
        "preset.minimal": "极简专业",
        "preset.noir": "黑白纪实",
        "preset.forest": "森林苔绿",
        "preset.sunset": "黄昏日落",
        "preset.ocean": "深海青蓝",
        "preset.paper": "纸本手账",
        "preset.unknown": "未知风格预设 {key!r}；可用：{known}",
        # ---- 配置校验 ----
        "config.set.missing_key": "--set 缺少键名",
        "config.lines.item": "{key} 的每一项都必须是字符串",
        "config.lines.type": "{key} 必须是字符串或字符串数组",
        "config.color.invalid": "颜色 {key}={value!r} 不是合法的十六进制色值（如 #02ADFB）",
        "config.size.invalid": "画布尺寸 {size!r} 格式不对，应形如 1200x900",
        "config.format.type": "format 必须是 png / svg / both，或其数组",
        "config.format.unknown": "format 只能是 png / svg / both，收到 {item!r}",
        "config.root.type": "配置文件顶层必须是对象（顶层写数组即为批量模式）",
        "config.title.missing": "缺少主标题：用 -t/--title 或在配置里写 title",
        "config.fonts.value": "fonts.{key} 必须是字体名或 .ttf 路径",
        "config.enum": "{name} 只能是 {values}",
        "config.range": "{name} 应在 {low} 到 {high} 之间",
        "config.font.missing": "未安装 {lang} 字体，请先运行 `pixellogo fonts install {lang}`",
        "config.batch.empty": "配置文件是空数组，没有可渲染的内容",
        "config.warn.unknown": "未知配置项 {key!r} 已忽略",
        "config.warn.color": "未知颜色项 colors.{key} 已忽略",
        "config.warn.font": "未知字体项 fonts.{key} 已忽略",
        "config.warn.layout": "未知排版项 layout.{key} 已忽略",
        # ---- 字体 ----
        "font.lang.unknown": "未知语言 {lang!r}；可用：{known}",
        "font.not_installed": ("未安装 {key} 字体。运行 `pixellogo fonts install {key}` 下载后重试，"
                               "或改用 --lang zh-hans"),
        "font.name.empty": "字体名为空",
        "font.bundled.missing": "内置字体缺失：{path}",
        "font.unknown": "未知字体 {name!r}；可用内置字体：{known}；或传入 .ttf 路径",
        "font.file.invalid": "不是有效的字体文件",
        "font.file.type": "不是有效的 TrueType/OpenType 字体",
        "font.cmap.missing": "字体缺少 cmap 表：{path}",
        "font.cmap.unicode": "字体没有可用的 Unicode cmap 子表：{path}",
        # ---- 字体包下载 ----
        "pack.exists": "{key} 字体已存在：{path}",
        "pack.downloading": "下载 {key} 字体包（{label}）…\n  {url}",
        "pack.download.failed": "下载失败：{error}\n可设置 PIXELLOGO_FONT_MIRROR 指向镜像目录后重试。",
        "pack.member.missing": "字体包内没有 {member}",
        "pack.zip.invalid": "下载到的文件不是有效 zip，可能被网络代理拦截",
        "pack.file.small": "字体文件异常（体积过小），已删除，请重试",
        "pack.installed": "已安装：{path}",
        # ---- 排版与输出 ----
        "layout.title.empty": "主标题不能为空",
        "render.format.unsupported": "不支持的输出格式 {fmt!r}；可选：{opts}",
        "render.format.suffix": "无法从扩展名推断格式：{name}",
        # ---- JSONC ----
        "jsonc.comment.unclosed": "块注释没有闭合：缺少 */",
        "jsonc.parse.failed": "配置解析失败（第 {line} 行第 {col} 列）：{msg}",
        "jsonc.file.missing": "配置文件不存在：{path}",
    },
}


def t(key: str, /, **kwargs) -> str:
    """取当前语言的文案；缺键时回退英语，再回退键名。

    ``key`` 是「仅位置参数」，这样调用方的占位符也可以叫 ``key``（如
    ``t("preset.unknown", key="nope", known=...)``）。
    """
    lang = get_language()
    text = MESSAGES.get(lang, {}).get(key) or MESSAGES[DEFAULT].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


# ---- argparse 内置报错的中文化 ----
# argparse 的 usage / error 前缀由本模块接管，其余固定句式用正则替换；
# 未匹配的句子保持原样，只在前面加上本地化的错误前缀。
_ARG_RULES: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"^argument ([^:]+): invalid choice: '([^']*)' \(choose from (.+)\)$"),
     "参数 {0} 的取值 {1!r} 无效；可选：{2}"),
    (re.compile(r"^argument ([^:]+): expected one argument$"),
     "参数 {0} 需要一个值"),
    (re.compile(r"^argument ([^:]+): invalid int value: '([^']*)'$"),
     "参数 {0} 需要整数值，收到 {1!r}"),
    (re.compile(r"^argument ([^:]+): invalid float value: '([^']*)'$"),
     "参数 {0} 需要数值，收到 {1!r}"),
    (re.compile(r"^unrecognized arguments: (.+)$"),
     "无法识别的参数：{0}"),
    (re.compile(r"^the following arguments are required: (.+)$"),
     "缺少必需参数：{0}"),
    (re.compile(r"^ambiguous option: (.+)$"),
     "参数缩写有歧义：{0}"),
)


def translate_argparse_error(message: str) -> str:
    """把 argparse 的英文报错换成当前语言；英文环境下原样返回。"""
    if not is_chinese():
        return message
    for pattern, template in _ARG_RULES:
        match = pattern.match(message)
        if match:
            return template.format(*match.groups())
    return message


__all__ = [
    "SUPPORTED",
    "DEFAULT",
    "ENV_VAR",
    "MESSAGES",
    "detect",
    "get_language",
    "set_language",
    "reset",
    "is_chinese",
    "join",
    "normalize",
    "t",
    "translate_argparse_error",
]
