"""排版引擎：把内容与样式铺进画布，产出 ``Scene``。

三种画布各有自己的排版走向（见 ``modes.py``），但共用同一套「行栈」模型：
文字先渲染成掩膜，再按基线节奏逐行叠放，最后统一做投影与装饰。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pixellogo import fonts as fontlib
from pixellogo import i18n
from pixellogo import text as textlib
from pixellogo.modes import Mode
from pixellogo.presets import Preset
from pixellogo.scene import Rect, Scene


#: 需要右侧装饰时，留给装饰的宽度占内容区的比例
MOTIF_RESERVE = 0.26

#: 副标题与说明缩字号的下限（再小就看不出像素网格了）
MIN_TEXT_SIZE = 9

#: 折行 + 缩字号：先按比例跳几次，再逐像素微调；到下限仍放不下就告警
FIT_JUMPS = 3


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
    wrap: bool = True            # 副标题 / 说明 / 小字标签超宽时自动折行
    colors: dict[str, str] = field(default_factory=dict)
    font_overrides: dict[str, str] = field(default_factory=dict)
    motif: str = "auto"          # auto | none | blocks
    pattern: str = "none"        # none | grid | dots | scanlines
    lang: str = "zh-hans"        # zh-hans | zh-hant | ja | ko


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


def _fallback(design: Design) -> list[str]:
    """中文字形回退：按 lang 选具体变体，缺失时由 config 层提前拦下。"""
    return [fontlib.cjk_font_path(design.lang)]


def _title_chain(design: Design) -> list[str]:
    return fontlib.resolve_chain(design.font_overrides.get("title") or design.preset.title_font,
                                 _fallback(design))


def _sub_chain(design: Design) -> list[str]:
    return fontlib.resolve_chain(design.font_overrides.get("sub") or design.preset.sub_font,
                                 _fallback(design))


def _body_chain(design: Design) -> list[str]:
    return fontlib.resolve_chain(design.font_overrides.get("body") or design.preset.body_font,
                                 _fallback(design))


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


def _block_side(thickness: int) -> int:
    """方块分隔线的边长；比线宽大得多，排版时必须按它预留高度。"""
    return max(thickness * 4, 10)


def _divider_height(thickness: int, style: str) -> int:
    """分隔线占用的垂直高度。line / dash 只有线宽，block 是一整块方阵。"""
    return _block_side(thickness) if style == "block" else thickness


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
        block = _block_side(thickness)
        gap = max(thickness * 2, 6)
        # 只放完整的方块，余下的像素平摊进间隙：既不出半块，也不越过右边界
        count = (width + gap) // (block + gap)
        if count <= 1:
            side = min(block, width)
            scene.add(Rect(x, y, side, side, color))
            return
        step = block + gap + (width - count * block) // (count - 1)
        cursor = x
        for _ in range(count):
            scene.add(Rect(cursor, y, block, block, color))
            cursor += step
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

    def boxed(mask) -> int:
        pad = max(5, int(round(size * 0.55)))
        return mask.width + pad * 2

    mask = textlib.line_mask(design.badge, size, chain, tracking=design.tracking)
    # 徽标是实心框，不折行；超宽时缩小字号直到放得进内容区
    while mask is not None and boxed(mask) > content_w and size > 9:
        size -= 1
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
    unit = int(min(area_w / 2.4, design.mode.height * 0.13))
    if unit < 10:
        return
    right = margin + content_w
    bottom = design.mode.height - margin
    # 用与底色有保证对比度的三种颜色，深色预设上投影色几乎看不见
    colors = [palette["primary"], palette["accent"], palette["fg"]]
    for index, color in enumerate(colors):
        x = right - (3 - index) * unit
        y = bottom - (index + 1) * unit
        scene.add(Rect(x, y, unit, unit, color))


def _visual_lines(lines: list[str], size: int, chain: list[str], text_w: int,
                  tracking: float, wrap: bool) -> list[str]:
    """把用户给的行展开成实际渲染行：开启折行时按文本区宽度折开。"""
    if not wrap:
        return [line for line in lines if line.strip()]
    result: list[str] = []
    for line in lines:
        result.extend(textlib.wrap_line(line, size, chain, text_w, tracking))
    return [line for line in result if line.strip()]


def build_scene(design: Design, diagnostics: list[str] | None = None) -> Scene:
    """把设计稿排成场景。

    ``diagnostics`` 传入列表时，排版过程中发现的问题（例如缩到最小字号仍放不下）
    会以本地化文案追加进去，由调用方决定怎么提示。
    """
    mode = design.mode
    palette = _resolve_colors(design)
    scene = Scene(width=mode.width, height=mode.height, background=palette["bg"])
    _draw_pattern(scene, palette, design.pattern)

    margin = max(6, int(round(min(mode.width, mode.height) * design.margin)))
    content_w = mode.width - margin * 2
    text_w = max(40, int(round(content_w * mode.text_ratio)))
    # 显式要求右侧装饰时，从文本区里让出位置，否则窄画布上装饰会被挤掉
    wants_motif = (design.motif == "blocks"
                   or (design.motif == "auto" and mode.motif == "blocks"))
    if wants_motif:
        text_w = min(text_w, max(40, content_w - int(round(content_w * MOTIF_RESERVE))))
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
        raise ValueError(i18n.t("layout.title.empty"))

    base_sub = max(MIN_TEXT_SIZE, int(round(mode.height * 0.042)))
    base_body = max(MIN_TEXT_SIZE, int(round(mode.height * 0.034)))
    eyebrow_size = max(8, int(round(mode.height * 0.026)))

    # 标题块最多占可用高度的一半，避免多行标题把副标题挤出画布
    auto_cap = max(12, min(int(mode.height * 0.42),
                           int((mode.height - margin * 2) * 0.55 / max(1, len(title_lines)))))
    start_size = design.title_size or int(round(mode.height * mode.title_ratio))
    # 显式指定字号时不做放大，只允许收缩
    title_size, title_masks = _fit_title(title_lines, title_chain, text_w, start_size,
                                         design.title_size or auto_cap, design)

    eyebrow_src = [prepared(design.eyebrow)] if design.eyebrow else []
    sub_src = [prepared(t) for t in design.subtitle]
    body_src = [prepared(t) for t in design.desc]

    thickness = max(2, int(round(mode.height * 0.010)))
    divider_w = max(12, int(round(text_w * design.divider_ratio)))
    available = mode.height - margin * 2

    def compose(sub_size: int, body_size: int):
        """按给定字号折行并堆叠，返回 (行栈, 内容总高, 分隔线位置)。"""
        stack = _Stack(design.leading)
        divider_at: int | None = None

        for line in _visual_lines(eyebrow_src, eyebrow_size, body_chain,
                                  text_w, design.tracking, design.wrap):
            mask = textlib.line_mask(line, eyebrow_size, body_chain, tracking=design.tracking)
            if mask:
                stack.line(mask, palette["accent"], "eyebrow")
                stack.gap(eyebrow_size * 0.16)
        if stack.items:
            stack.gap(title_size * 0.18)

        for mask in title_masks:
            stack.line(mask, palette["primary"], "title")
            stack.gap(title_size * 0.04)

        sub_masks = [m for m in (textlib.line_mask(line, sub_size, sub_chain,
                                                  tracking=design.tracking)
                                 for line in _visual_lines(sub_src, sub_size, sub_chain,
                                                           text_w, design.tracking, design.wrap))
                     if m]
        if sub_masks:
            stack.gap(title_size * 0.20)
            for mask in sub_masks:
                stack.line(mask, palette["fg"], "sub")
                stack.gap(sub_size * 0.35)

        if divider != "none":
            stack.gap(max(6, int((sub_size if sub_masks else title_size) * 0.6)))
            divider_at = stack.cursor
            stack.gap(_divider_height(thickness, divider))
            stack.gap(max(6, int(body_size * 0.8)))

        for mask in (m for m in (textlib.line_mask(line, body_size, body_chain,
                                                   tracking=design.tracking)
                                 for line in _visual_lines(body_src, body_size, body_chain,
                                                           text_w, design.tracking, design.wrap))
                     if m):
            stack.line(mask, palette["fg"], "body")
            stack.gap(body_size * 0.35)

        total = max((offset + mask.line_height for mask, offset, _c, _k in stack.items),
                    default=0)
        extent = total
        if divider_at is not None:
            if divider == "block":
                # 方块分隔线是一整个方块高，不能按线宽估算
                extent = max(extent, divider_at + _block_side(thickness))
            else:
                # 分隔线两端的方块会伸出行高之外，判定溢出时要把它算进去
                cap = max(6, thickness * 3)
                extent = max(extent, divider_at - cap // 2 + thickness // 2 + cap)
        return stack, total, divider_at, extent

    # 垂直放不下时缩小副标题与说明的字号，再重新折行重排：
    # 先按总高比例跳几次（快），再逐像素微调（准），直到放得下或触到下限
    sub_size, body_size = base_sub, base_body
    stack, total, divider_at, extent = compose(sub_size, body_size)
    for _ in range(FIT_JUMPS):
        if extent <= available:
            break
        factor = available / extent
        next_sub = max(MIN_TEXT_SIZE, int(sub_size * factor))
        next_body = max(MIN_TEXT_SIZE, int(body_size * factor))
        if (next_sub, next_body) == (sub_size, body_size):
            break
        sub_size, body_size = next_sub, next_body
        stack, total, divider_at, extent = compose(sub_size, body_size)

    while extent > available and (sub_size > MIN_TEXT_SIZE or body_size > MIN_TEXT_SIZE):
        sub_size = max(MIN_TEXT_SIZE, sub_size - 1)
        body_size = max(MIN_TEXT_SIZE, body_size - 1)
        stack, total, divider_at, extent = compose(sub_size, body_size)

    if extent > available and diagnostics is not None:
        diagnostics.append(i18n.t("layout.warn.overflow", total=extent,
                                  available=available, size=min(sub_size, body_size)))

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


def missing_glyph_warnings(design: Design) -> list[str]:
    """检查该设计真正会用到的字体能否覆盖全部文字，返回缺字告警。

    与 :func:`build_scene` 走同一套字体挑选逻辑（``pick_unified``），因此报出来的
    缺字就是最终会渲染成方块的那几个字。同一款字体的缺字合并成一条告警。
    未安装的字形变体不会在这里报错：内容里没有对应文字时本就不算错误。
    """
    try:
        chains = (_title_chain(design), _sub_chain(design), _body_chain(design))
    except fontlib.FontError:
        return []
    title_chain, sub_chain, body_chain = chains

    def prepared(value: str) -> str:
        text = value.upper() if design.uppercase else value
        return text.strip()

    checks: list[tuple[list[str], str]] = [(title_chain, line)
                                           for line in design.title.split("\n")]
    checks.append((body_chain, design.eyebrow))
    checks.extend((sub_chain, line) for line in design.subtitle)
    checks.extend((body_chain, line) for line in design.desc)
    checks.append((body_chain, design.badge))

    missing_by_font: dict[str, list[str]] = {}
    for chain, raw in checks:
        text = prepared(raw)
        if not text:
            continue
        chosen = fontlib.pick_unified(text, chain)
        bucket = missing_by_font.setdefault(chosen, [])
        for char in fontlib.missing_chars(chosen, text):
            if char not in bucket:
                bucket.append(char)
        if not bucket:
            missing_by_font.pop(chosen, None)

    return [i18n.t("config.warn.glyph", font=Path(chosen).name, chars="".join(chars))
            for chosen, chars in missing_by_font.items()]
