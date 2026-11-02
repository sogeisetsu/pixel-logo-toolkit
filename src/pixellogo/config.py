"""配置合并与校验：默认值 → 预设 → 配置文件 → 命令行。

合并结果最终变成一份 ``Design``，排版层只认 ``Design``，不关心参数从哪来。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from pixellogo import fonts as fontlib
from pixellogo import modes as modes_mod
from pixellogo.layout import Design
from pixellogo.presets import Preset, get_preset

COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

TOP_KEYS = {
    "mode", "size", "preset", "title", "subtitle", "desc", "eyebrow", "badge",
    "colors", "fonts", "layout", "output", "scale", "out", "format", "lang",
}
COLOR_KEYS = {"bg", "fg", "primary", "accent", "shadow"}
FONT_KEYS = {"title", "sub", "body"}
LAYOUT_KEYS = {
    "align", "vertical", "margin", "divider", "dividerWidth",
    "divider-width", "titleSize", "title-size", "motif", "shadowOffset", "shadow-offset",
    "cjkBold", "cjk-bold", "tracking", "leading", "uppercase", "pattern",
}

ALIGN_VALUES = {"auto", "left", "center"}
VERTICAL_VALUES = {"auto", "top", "center"}
DIVIDER_VALUES = {"auto", "line", "dash", "block", "none"}
MOTIF_VALUES = {"auto", "none", "blocks"}
PATTERN_VALUES = {"none", "grid", "dots", "scanlines"}


class ConfigError(ValueError):
    """配置不合法。"""


@dataclass
class Settings:
    """一次运行的最终设置。"""

    design: Design
    scale: int
    out: str
    formats: list[str] = field(default_factory=lambda: ["png"])
    merged: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def mode_key(self) -> str:
        return self.design.mode.key

    def describe(self) -> dict:
        """供 ``--dry-run`` 输出的可读快照。"""
        design = self.design
        return {
            "mode": design.mode.key,
            "canvas": {
                "logical": [design.mode.width, design.mode.height],
                "output": [design.mode.width * self.scale, design.mode.height * self.scale],
                "scale": self.scale,
            },
            "preset": design.preset.key,
            "content": {
                "title": design.title,
                "subtitle": design.subtitle,
                "desc": design.desc,
                "eyebrow": design.eyebrow,
                "badge": design.badge,
            },
            "colors": {
                "bg": design.colors.get("bg") or design.preset.bg,
                "fg": design.colors.get("fg") or design.preset.fg,
                "primary": design.colors.get("primary") or design.preset.primary,
                "accent": design.colors.get("accent") or design.preset.accent,
                "shadow": design.colors.get("shadow") or design.preset.shadow,
            },
            "layout": {
                "align": design.align,
                "vertical": design.vertical,
                "margin": design.margin,
                "divider": design.divider,
                "dividerRatio": design.divider_ratio,
                "titleSize": design.title_size or "auto",
                "shadowOffset": design.shadow_offset,
                "motif": design.motif,
            },
            "output": {"path": self.out, "format": self.formats},
        }


def deep_merge(base: dict, override: dict) -> dict:
    """字典递归合并；列表整体替换（便于用配置文件覆盖副标题行）。"""
    result = dict(base)
    for key, value in override.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def coerce(raw: str):
    """把 ``--set key=value`` 的字符串转成合适的类型。"""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def set_path(data: dict, path: str, value) -> None:
    """按点路径写值，例如 ``colors.primary=#fff``。"""
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ConfigError("--set 缺少键名")
    cursor = data
    for part in parts[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[parts[-1]] = value


def as_lines(value, key: str) -> list[str]:
    """把字符串或字符串数组统一成行列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.split("\n") if line.strip()]
    if isinstance(value, (list, tuple)):
        lines: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ConfigError(f"{key} 的每一项都必须是字符串")
            lines.extend(part.strip() for part in item.split("\n") if part.strip())
        return lines
    raise ConfigError(f"{key} 必须是字符串或字符串数组")


def _pick_color(colors: dict, key: str) -> str | None:
    value = colors.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not COLOR_RE.match(value):
        raise ConfigError(f"颜色 {key}={value!r} 不是合法的十六进制色值（如 #02ADFB）")
    return value


def _layout_value(layout: dict, *names):
    for name in names:
        if name in layout and layout[name] is not None:
            return layout[name]
    return None


def validate(merged: dict) -> list[str]:
    """检查未知键，返回告警列表。"""
    warnings: list[str] = []
    for key in merged:
        if key not in TOP_KEYS:
            warnings.append(f"未知配置项 {key!r} 已忽略")
    colors = merged.get("colors") or {}
    for key in colors:
        if key not in COLOR_KEYS:
            warnings.append(f"未知颜色项 colors.{key} 已忽略")
    fonts = merged.get("fonts") or {}
    for key in fonts:
        if key not in FONT_KEYS:
            warnings.append(f"未知字体项 fonts.{key} 已忽略")
    layout = merged.get("layout") or {}
    for key in layout:
        if key not in LAYOUT_KEYS:
            warnings.append(f"未知排版项 layout.{key} 已忽略")
    return warnings


def cli_to_config(args) -> dict:
    """把 argparse 结果转成配置字典，只保留命令行显式给出的项。"""
    data: dict = {}

    def put(key, value):
        if value is not None and value != "" and value != []:
            data[key] = value

    put("title", args.title)
    put("subtitle", args.subtitle)
    put("desc", args.desc)
    put("eyebrow", args.eyebrow)
    put("badge", args.badge)
    put("preset", args.preset)
    put("mode", args.mode)
    put("size", args.size)
    put("scale", args.scale)
    put("out", args.out)
    put("format", getattr(args, "format", None))
    put("lang", getattr(args, "lang", None))

    colors = {}
    for key, value in (("bg", args.bg), ("fg", args.fg), ("primary", args.primary),
                       ("accent", args.accent), ("shadow", args.shadow_color)):
        if value:
            colors[key] = value
    if colors:
        data["colors"] = colors

    fonts = {}
    for key, value in (("title", args.font_title), ("sub", args.font_sub), ("body", args.font_body)):
        if value:
            fonts[key] = value
    if fonts:
        data["fonts"] = fonts

    layout = {}
    if args.align and args.align != "auto":
        layout["align"] = args.align
    if args.vertical and args.vertical != "auto":
        layout["vertical"] = args.vertical
    if args.margin is not None:
        layout["margin"] = args.margin
    if args.divider and args.divider != "auto":
        layout["divider"] = args.divider
    if args.divider_width is not None:
        layout["dividerWidth"] = args.divider_width
    if args.title_size is not None:
        layout["titleSize"] = args.title_size
    if args.motif and args.motif != "auto":
        layout["motif"] = args.motif
    if args.shadow_offset is not None:
        layout["shadowOffset"] = args.shadow_offset
    if getattr(args, "tracking", None) is not None:
        layout["tracking"] = args.tracking
    if getattr(args, "leading", None) is not None:
        layout["leading"] = args.leading
    if getattr(args, "uppercase", False):
        layout["uppercase"] = True
    if getattr(args, "bg_pattern", None):
        layout["pattern"] = args.bg_pattern
    if layout:
        data["layout"] = layout

    return data


def _build_mode(merged: dict) -> modes_mod.Mode:
    size = merged.get("size")
    if size:
        try:
            width, height = (int(part) for part in str(size).lower().replace("*", "x").split("x"))
        except (ValueError, TypeError):
            raise ConfigError(f"画布尺寸 {size!r} 格式不对，应形如 1200x900") from None
        return modes_mod.custom_mode(width, height)
    return modes_mod.get_mode(str(merged.get("mode", modes_mod.DEFAULT_MODE)))


def _build_preset(merged: dict) -> Preset:
    return get_preset(str(merged.get("preset", "terminal")))


def _parse_formats(merged: dict) -> list[str]:
    """把 format 配置规范成按顺序去的格式列表。"""
    raw = merged.get("format")
    if raw is None:
        raw = (merged.get("output") or {}).get("formats")
    if raw is None:
        return ["png", "svg"]
    items = [raw] if isinstance(raw, str) else list(raw) if isinstance(raw, (list, tuple)) else None
    if items is None:
        raise ConfigError("format 必须是 png / svg / both，或其数组")
    result: list[str] = []
    for item in items:
        key = str(item).lower()
        if key == "both":
            expanded = ["png", "svg"]
        elif key in ("png", "svg"):
            expanded = [key]
        else:
            raise ConfigError(f"format 只能是 png / svg / both，收到 {item!r}")
        for fmt in expanded:
            if fmt not in result:
                result.append(fmt)
    return result


def resolve(file_data, cli_data: dict, forced_out: str | None = None) -> Settings:
    """合并配置并构造 ``Settings``。"""
    if file_data is not None and not isinstance(file_data, dict):
        raise ConfigError("配置文件顶层必须是对象（批量模式请用 --batch）")

    merged = deep_merge({}, file_data or {})
    merged = deep_merge(merged, cli_data)

    warnings = validate(merged)
    mode = _build_mode(merged)
    preset = _build_preset(merged)

    title = merged.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ConfigError("缺少主标题：用 -t/--title 或在配置里写 title")

    colors_cfg = merged.get("colors") or {}
    colors = {key: _pick_color(colors_cfg, key) for key in COLOR_KEYS}
    colors = {key: value for key, value in colors.items() if value}

    fonts_cfg = merged.get("fonts") or {}
    for key in fonts_cfg:
        if not isinstance(fonts_cfg[key], str):
            raise ConfigError(f"fonts.{key} 必须是字体名或 .ttf 路径")

    layout_cfg = merged.get("layout") or {}
    align = str(_layout_value(layout_cfg, "align") or "auto")
    vertical = str(_layout_value(layout_cfg, "vertical") or "auto")
    divider = str(_layout_value(layout_cfg, "divider") or "auto")
    motif = str(_layout_value(layout_cfg, "motif") or "auto")
    if align not in ALIGN_VALUES:
        raise ConfigError(f"align 只能是 {'/'.join(sorted(ALIGN_VALUES))}")
    if vertical not in VERTICAL_VALUES:
        raise ConfigError(f"vertical 只能是 {'/'.join(sorted(VERTICAL_VALUES))}")
    if divider not in DIVIDER_VALUES:
        raise ConfigError(f"divider 只能是 {'/'.join(sorted(DIVIDER_VALUES))}")
    if motif not in MOTIF_VALUES:
        raise ConfigError(f"motif 只能是 {'/'.join(sorted(MOTIF_VALUES))}")

    pattern = str(_layout_value(layout_cfg, "pattern") or "none")
    if pattern not in PATTERN_VALUES:
        raise ConfigError(f"pattern 只能是 {'/'.join(sorted(PATTERN_VALUES))}")

    margin = _layout_value(layout_cfg, "margin")
    if margin is None:
        margin = 0.06
    margin = float(margin)
    if not 0 <= margin < 0.4:
        raise ConfigError("margin 应在 0 到 0.4 之间")

    divider_ratio = _layout_value(layout_cfg, "dividerWidth", "divider-width")
    divider_ratio = 0.42 if divider_ratio is None else float(divider_ratio)
    if not 0.05 <= divider_ratio <= 1.0:
        raise ConfigError("dividerWidth 应在 0.05 到 1.0 之间")

    shadow_offset = _layout_value(layout_cfg, "shadowOffset", "shadow-offset")
    shadow_offset = 1 if shadow_offset is None else int(shadow_offset)
    if not 0 <= shadow_offset <= 4:
        raise ConfigError("shadowOffset 应在 0 到 4 之间")

    title_size = _layout_value(layout_cfg, "titleSize", "title-size")
    title_size = None if title_size is None else int(title_size)

    cjk_bold = _layout_value(layout_cfg, "cjkBold", "cjk-bold")
    cjk_bold = 0.018 if cjk_bold is None else float(cjk_bold)

    tracking = _layout_value(layout_cfg, "tracking")
    tracking = 1.0 if tracking is None else float(tracking)
    if not 0.5 <= tracking <= 1.5:
        raise ConfigError("tracking 应在 0.5 到 1.5 之间")

    leading = _layout_value(layout_cfg, "leading")
    leading = 1.0 if leading is None else float(leading)
    if not 0.8 <= leading <= 2.0:
        raise ConfigError("leading 应在 0.8 到 2.0 之间")

    uppercase = bool(_layout_value(layout_cfg, "uppercase"))

    lang = fontlib.normalize_lang(str(merged.get("lang") or fontlib.DEFAULT_LANG))
    if lang not in fontlib.BUNDLED_VARIANTS:
        try:
            fontlib.cjk_font_path(lang)
        except fontlib.FontError:
            # 只有内容里真的出现中日韩字符时才强制要求安装
            sample = " ".join([title, *as_lines(merged.get("subtitle"), "subtitle"),
                               *as_lines(merged.get("desc"), "desc"),
                               str(merged.get("eyebrow") or ""), str(merged.get("badge") or "")])
            if any("\u2e80" <= char <= "\u9fff" for char in sample):
                raise ConfigError(
                    f"未安装 {lang} 字体，请先运行 `pixellogo fonts install {lang}`"
                ) from None
    scale = merged.get("scale")
    scale = int(scale) if scale else mode.scale
    if not 1 <= scale <= 8:
        raise ConfigError("scale 应在 1 到 8 之间")

    out_cfg = merged.get("output") or {}
    out = forced_out or merged.get("out") or out_cfg.get("path") or out_cfg.get("dir") or "out"
    if merged.get("scale") is None and out_cfg.get("scale"):
        scale = int(out_cfg["scale"])

    design = Design(
        title=title.strip(),
        preset=preset,
        mode=mode,
        subtitle=as_lines(merged.get("subtitle"), "subtitle"),
        desc=as_lines(merged.get("desc"), "desc"),
        eyebrow=str(merged.get("eyebrow") or ""),
        badge=str(merged.get("badge") or ""),
        align=align,
        vertical=vertical,
        margin=margin,
        shadow_offset=shadow_offset,
        divider=divider,
        divider_ratio=divider_ratio,
        title_size=title_size,
        cjk_bold=cjk_bold,
        tracking=tracking,
        leading=leading,
        uppercase=uppercase,
        motif=motif,
        pattern=pattern,
        lang=lang,
        colors=colors,
        font_overrides={key: value for key, value in fonts_cfg.items() if isinstance(value, str)},
    )
    return Settings(design=design, scale=scale, out=str(out), formats=_parse_formats(merged),
                    merged=merged, warnings=warnings)


def resolve_many(file_data, cli_data: dict, forced_out: str | None = None) -> list[Settings]:
    """配置文件顶层是数组时批量解析，否则等价于单个 ``resolve``。"""
    if isinstance(file_data, list):
        if not file_data:
            raise ConfigError("配置文件是空数组，没有可渲染的内容")
        return [resolve(item, cli_data, forced_out) for item in file_data]
    return [resolve(file_data, cli_data, forced_out)]
