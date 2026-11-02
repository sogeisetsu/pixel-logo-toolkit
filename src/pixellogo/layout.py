"""排版引擎：把内容与样式铺进画布，产出 ``Scene``。

三种画布各有自己的排版走向（见 ``modes.py``），但共用同一套「行栈」模型：
文字先渲染成掩膜，再按基线节奏逐行叠放，最后统一做投影与装饰。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pixellogo import fonts as fontlib
from pixellogo import text as textlib
from pixellogo.modes import Mode
from pixellogo.presets import Preset
from pixellogo.scene import Rect, Scene


@dataclass
class Design:
    """一次渲染的完整输入（已解析、已合并默认值）。"""

    title: str
    preset: Preset
    mode: Mode
    subtitle: list[str] = field(default_factory=list)
    desc: list[str] = field(default_factory=list)
    eyebrow: str = ""
    badge: str = ""
    align: str = "auto"          # auto | left | center
    vertical: str = "auto"       # auto | top | center
    margin: float = 0.06
    shadow_offset: int = 1
    divider: str = "auto"        # auto | line | dash | block | none
    divider_ratio: float = 0.42
    title_size: int | None = None
    cjk_bold: float = 0.018
    tracking: float = 1.0
    leading: float = 1.0
    uppercase: bool = False
    colors: dict[str, str] = field(default_factory=dict)
    font_overrides: dict[str, str] = field(default_factory=dict)
    motif: str = "auto"          # auto | none | blocks
    pattern: str = "none"        # none | grid | dots | scanlines


def _resolve_colors(design: Design) -> dict[str, str]:
    preset = design.preset
    palette = {
        "bg": design.colors.get("bg") or preset.bg,
        "fg": design.colors.get("fg") or preset.fg,
        "primary": design.colors.get("primary") or preset.primary,
        "accent": design.colors.get("accent") or preset.accent,
        "shadow": design.colors.get("shadow") or preset.shadow,
    }
    return palette


def _title_chain(design: Design) -> list[str]:
    return fontlib.resolve_chain(design.font_overrides.get("title") or design.preset.title_font)


def _sub_chain(design: Design) -> list[str]:
    return fontlib.resolve_chain(design.font_overrides.get("sub") or design.preset.sub_font)


def _body_chain(design: Design) -> list[str]:
    return fontlib.resolve_chain(design.font_overrides.get("body") or design.preset.body_font)


def _bold_for(text: str, chain: list[str], size: int, design: Design) -> int:
    """中文像素字体笔画偏细，标题命中回退字体时按比例加粗。"""
    if design.cjk_bold <= 0:
        return 0
    if fontlib.pick_unified(text, chain) == chain[0]:
        return 0
    return max(0, int(round(size * design.cjk_bold)))


def _fit_title(lines: list[str], chain: list[str], text_w: int, start: int,
               cap: int, design: Design) -> tuple[int, list[textlib.TextMask]]:
    """先按可用宽度收缩，再把短标题放大到接近撑满。

    收放都走整数像素，避免出现半像素坐标。
    """

    def render(size: int) -> list[textlib.TextMask]:
        masks = []
        for line in lines:
            mask = textlib.line_mask(line, size, chain,
                                     bold_px=_bold_for(line, chain, size, design),
                                     tracking=design.tracking)
            if mask is not None:
                masks.append(mask)
        return masks

    def widest(size: int) -> int:
        return max((m.width for m in render(size)), default=0)

    minimum = 10
    size = max(minimum, min(int(start), cap))
    while widest(size) > text_w and size > minimum:
        size = max(minimum, int(size * 0.94))
    while size < cap:
        candidate = min(cap, max(size + 1, int(size * 1.06)))
        if widest(candidate) <= text_w:
            size = candidate
        else:
            break
    return size, render(size)


class _Stack:
    """按基线节奏堆叠文字行，返回每行的相对偏移。"""

    def __init__(self, leading: float = 1.0) -> None:
        self.cursor = 0
        self.leading = leading
        self.items: list[tuple[textlib.TextMask, int, str, str]] = []

    def gap(self, px: int) -> None:
        self.cursor += max(0, int(px))

    def line(self, mask: textlib.TextMask, color: str, kind: str) -> None:
        self.items.append((mask, self.cursor, color, kind))
        self.cursor += max(1, int(round(mask.line_height * self.leading)))


def _draw_divider(scene: Scene, x: int, y: int, width: int, thickness: int,
                  color: str, style: str) -> None:
    if width <= 0 or thickness <= 0 or style == "none":
        return
    if style == "dash":
        dash = max(thickness * 3, 8)
        step = dash + max(thickness * 2, 6)
        cursor = x
        while cursor < x + width:
            scene.add(Rect(cursor, y, min(dash, x + width - cursor), thickness, color))
            cursor += step
        return
    if style == "block":
        block = max(thickness * 4, 10)
        cursor = x
        while cursor < x + width:
            scene.add(Rect(cursor, y, min(block, x + width - cursor), block, color))
            cursor += block + max(thickness * 2, 6)
        return
    scene.add(Rect(x, y, width, thickness, color))
    cap = max(6, thickness * 3)
    scene.add(Rect(x + width - cap, y - cap // 2 + thickness // 2, cap, cap, color))


def _draw_badge(scene: Scene, design: Design, palette: dict[str, str], margin: int,
                body_size: int, content_w: int) -> None:
    if not design.badge:
        return
    chain = _body_chain(design)
    size = max(9, int(round(body_size * 0.9)))
    mask = textlib.line_mask(design.badge, size, chain, tracking=design.tracking)
    if mask is None:
        return
    pad_x = max(5, int(round(size * 0.55)))
    pad_y = max(3, int(round(size * 0.35)))
    box_w = mask.width + pad_x * 2
    box_h = mask.height + pad_y * 2
    x = margin + content_w - box_w
    y = margin
    scene.add(Rect(x, y, box_w, box_h, palette["accent"]))
    scene.extend(textlib.mask_rects(mask.image, x + pad_x, y + pad_y, palette["bg"]))


def _mix(first: str, second: str, ratio: float) -> str:
    """把两个色值按比例混合成一个新的纯色（不引入透明度）。"""
    def parts(color: str) -> tuple[int, int, int]:
        value = color.lstrip("#")
        if len(value) == 3:
            value = "".join(char * 2 for char in value)
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]

    left, right = parts(first), parts(second)
    mixed = [round(a + (b - a) * ratio) for a, b in zip(left, right)]
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


def _draw_pattern(scene: Scene, palette: dict[str, str], pattern: str) -> None:
    """背景纹理：全部由整数矩形拼成，不引入渐变或半透明。"""
    if pattern == "none":
        return
    color = _mix(palette["bg"], palette["fg"], 0.10)
    width, height = scene.width, scene.height
    cell = max(10, round(min(width, height) / 20))

    if pattern == "grid":
        for x in range(cell, width, cell):
            scene.add(Rect(x, 0, 1, height, color))
        for y in range(cell, height, cell):
            scene.add(Rect(0, y, width, 1, color))
    elif pattern == "dots":
        dot = max(2, cell // 9)
        for x in range(cell, width, cell):
            for y in range(cell, height, cell):
                scene.add(Rect(x, y, dot, dot, color))
    elif pattern == "scanlines":
        gap = max(4, cell // 4)
        for y in range(0, height, gap):
            scene.add(Rect(0, y, width, 1, color))


def _draw_motif(scene: Scene, design: Design, palette: dict[str, str],
                margin: int, content_w: int, text_w: int) -> None:
    """OG 模式右侧的像素阶梯装饰。"""
    if design.motif == "none":
        return
    if design.motif == "auto" and design.mode.motif != "blocks":
        return
    area_x = margin + text_w + margin // 2
    area_w = margin + content_w - area_x
    # 右下角三级像素阶梯，贴着右边距收口
    unit = int(min(area_w / 2.4, design.mode.height * 0.15))
    if unit < 10:
        return
    right = margin + content_w
    bottom = design.mode.height - margin
    colors = [palette["shadow"], palette["primary"], palette["accent"]]
    for index, color in enumerate(colors):
        x = right - (3 - index) * unit
        y = bottom - (index + 1) * unit
        scene.add(Rect(x, y, unit, unit, color))


def build_scene(design: Design) -> Scene:
    """把设计稿排成场景。"""
    mode = design.mode
    palette = _resolve_colors(design)
    scene = Scene(width=mode.width, height=mode.height, background=palette["bg"])
    _draw_pattern(scene, palette, design.pattern)

    margin = max(6, int(round(min(mode.width, mode.height) * design.margin)))
    content_w = mode.width - margin * 2
    text_w = max(40, int(round(content_w * mode.text_ratio)))
    align = design.align if design.align != "auto" else mode.align
    vertical = design.vertical if design.vertical != "auto" else mode.vertical
    divider = design.divider if design.divider != "auto" else design.preset.divider

    title_chain = _title_chain(design)
    sub_chain = _sub_chain(design)
    body_chain = _body_chain(design)

    def prepared(value: str) -> str:
        return value.upper() if design.uppercase else value

    title_lines = [prepared(line.strip()) for line in design.title.split("\n") if line.strip()]
    if not title_lines:
        raise ValueError("主标题不能为空")

    sub_size = max(9, int(round(mode.height * 0.042)))
    body_size = max(9, int(round(mode.height * 0.034)))
    eyebrow_size = max(8, int(round(mode.height * 0.026)))

    # 标题块最多占可用高度的一半，避免多行标题把副标题挤出画布
    auto_cap = max(12, min(int(mode.height * 0.42),
                           int((mode.height - margin * 2) * 0.55 / max(1, len(title_lines)))))
    start_size = design.title_size or int(round(mode.height * mode.title_ratio))
    # 显式指定字号时不做放大，只允许收缩
    title_size, title_masks = _fit_title(title_lines, title_chain, text_w, start_size,
                                         design.title_size or auto_cap, design)

    eyebrow_mask = (textlib.line_mask(prepared(design.eyebrow), eyebrow_size, body_chain,
                                     tracking=design.tracking) if design.eyebrow else None)
    sub_masks = [m for m in (textlib.line_mask(prepared(t), sub_size, sub_chain,
                                               tracking=design.tracking) for t in design.subtitle) if m]
    body_masks = [m for m in (textlib.line_mask(prepared(t), body_size, body_chain,
                                                tracking=design.tracking) for t in design.desc) if m]

    thickness = max(2, int(round(mode.height * 0.010)))
    divider_w = max(12, int(round(text_w * design.divider_ratio)))

    stack = _Stack(design.leading)
    divider_at: int | None = None
    if eyebrow_mask:
        stack.line(eyebrow_mask, palette["accent"], "eyebrow")
        stack.gap(title_size * 0.18)
    for mask in title_masks:
        stack.line(mask, palette["primary"], "title")
        stack.gap(title_size * 0.04)
    if sub_masks:
        stack.gap(title_size * 0.20)
        for mask in sub_masks:
            stack.line(mask, palette["fg"], "sub")
            stack.gap(sub_size * 0.35)
    if divider != "none":
        stack.gap(max(6, int((sub_size if sub_masks else title_size) * 0.6)))
        divider_at = stack.cursor
        stack.gap(thickness)
        stack.gap(max(6, int(body_size * 0.8)))
    for mask in body_masks:
        stack.line(mask, palette["fg"], "body")
        stack.gap(body_size * 0.35)

    total = max((offset + mask.line_height for mask, offset, _c, _k in stack.items), default=0)
    available = mode.height - margin * 2
    if vertical == "top":
        origin_y = margin
    else:
        origin_y = margin + max(0, (available - total) // 2)

    shadow_dx = int(round(title_size * design.preset.shadow_ratio)) * design.shadow_offset

    for mask, offset, color, kind in stack.items:
        y = origin_y + offset
        if align == "center":
            x = margin + max(0, (text_w - mask.width) // 2)
        else:
            x = margin
        rects = textlib.mask_rects(mask.image, x, y, color)
        if kind == "title" and shadow_dx > 0:
            scene.extend(textlib.shadow_rects(rects, shadow_dx, shadow_dx, palette["shadow"]))
        scene.extend(rects)

    if divider_at is not None:
        if align == "center":
            divider_x = margin + max(0, (text_w - divider_w) // 2)
        else:
            divider_x = margin
        _draw_divider(scene, divider_x, origin_y + divider_at, divider_w, thickness,
                      palette["accent"], divider)

    _draw_badge(scene, design, palette, margin, body_size, content_w)
    _draw_motif(scene, design, palette, margin, content_w, text_w)
    return scene


def palette_of(design: Design) -> dict[str, str]:
    return _resolve_colors(design)
