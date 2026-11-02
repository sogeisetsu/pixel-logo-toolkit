"""文字栅格化：把一行文字变成可复用的像素掩膜。

流程是 ``文字 → alpha 掩膜 → 水平游程 → 矩形``，全程不产生任何平滑边缘：
掩膜按 128 阈值二值化，再按行合并成长条矩形，因此放大后每条边都是方块。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from pixellogo import fonts as fontlib
from pixellogo.scene import Rect

THRESHOLD = 128


@dataclass
class TextMask:
    """一行文字的二值掩膜及其排版信息。"""

    image: Image.Image
    width: int
    height: int
    #: 基线在该掩膜内的 y 偏移，用于多字体混排时对齐
    baseline: int
    #: 该行的正常行高（ascent + descent），用于保持统一的行走间距
    line_height: int

    def crop_top(self, y: int) -> int:
        return y


@lru_cache(maxsize=96)
def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _group_runs(text: str, chain: list[str]) -> list[tuple[str, str]]:
    """把文字按「所用字体」切成连续片段。"""
    runs: list[tuple[str, str]] = []
    for char in text:
        path = fontlib.pick_per_char(char, chain)
        if runs and runs[-1][0] == path:
            runs[-1] = (path, runs[-1][1] + char)
        else:
            runs.append((path, char))
    return runs


def line_mask(
    text: str,
    size: int,
    chain: list[str],
    unify: bool = True,
    bold_px: int = 0,
    tracking: float = 1.0,
) -> TextMask | None:
    """渲染一行文字，返回二值掩膜；空字符串返回 ``None``。

    ``unify=True`` 时整行只用一款字体（中英混排时优先中文像素字体），
    避免同一行出现两种笔画粗细；``False`` 时逐字回退。
    ``tracking`` 是字距倍率，``1.0`` 为字体原始步进，小于 1 更紧凑。
    """
    if not text:
        return None
    size = max(4, int(size))

    if unify:
        path = fontlib.pick_unified(text, chain)
        runs = [(path, text)]
    else:
        runs = _group_runs(text, chain)

    metrics = [(load_font(path, size), part) for path, part in runs]
    ascents = [font.getmetrics()[0] for font, _ in metrics]
    descents = [font.getmetrics()[1] for font, _ in metrics]
    ascent = max(ascents)
    descent = max(descents)
    line_height = ascent + descent

    def advance_of(font, part: str) -> int:
        if tracking == 1.0:
            return int(round(font.getlength(part)))
        # 逐字累加，才能对字距做非整数缩放
        return sum(int(round(font.getlength(char) * tracking)) for char in part)

    pad = size + bold_px * 2 + 4
    advance = sum(advance_of(font, part) for font, part in metrics)
    canvas_w = advance + pad * 2
    canvas_h = line_height + pad * 2

    canvas = Image.new("L", (canvas_w, canvas_h), 0)
    draw = ImageDraw.Draw(canvas)
    baseline_y = pad + ascent
    pen = pad
    for font, part in metrics:
        top = baseline_y - font.getmetrics()[0]
        if tracking == 1.0:
            draw.text((pen, top), part, font=font, fill=255)
        else:
            for char in part:
                draw.text((pen, top), char, font=font, fill=255)
                pen += int(round(font.getlength(char) * tracking))
            continue
        pen += int(round(font.getlength(part)))

    if bold_px > 0:
        radius = int(bold_px)
        canvas = canvas.filter(ImageFilter.MaxFilter(radius * 2 + 1))

    bbox = canvas.getbbox()
    if not bbox:
        return None
    cropped = canvas.crop(bbox)
    return TextMask(
        image=cropped,
        width=cropped.width,
        height=cropped.height,
        baseline=baseline_y - bbox[1],
        line_height=line_height,
    )


def mask_rects(mask: Image.Image, x: int, y: int, fill: str) -> list[Rect]:
    """掩膜 → 矩形列表：先按行取游程，再把上下完全相同的游程合并成整块。"""
    width, height = mask.size
    pixels = mask.load()
    rects: list[Rect] = []

    # 每一行：[(起始x, 宽度), ...]
    rows: list[list[tuple[int, int]]] = []
    for yy in range(height):
        runs: list[tuple[int, int]] = []
        start = None
        for xx in range(width):
            solid = pixels[xx, yy] > THRESHOLD
            if solid and start is None:
                start = xx
            elif not solid and start is not None:
                runs.append((start, xx - start))
                start = None
        if start is not None:
            runs.append((start, width - start))
        rows.append(runs)

    # 把连续且完全相同的行合并成更高的矩形
    index = 0
    while index < height:
        runs = rows[index]
        if not runs:
            index += 1
            continue
        span = 1
        while index + span < height and rows[index + span] == runs:
            span += 1
        for run_x, run_w in runs:
            rects.append(Rect(x + run_x, y + index, run_w, span, fill))
        index += span
    return rects


def shadow_rects(rects: list[Rect], offset_x: int, offset_y: int, fill: str) -> list[Rect]:
    """由主体矩形直接派生投影层：只偏移，不重新绘制。"""
    return [Rect(r.x + offset_x, r.y + offset_y, r.w, r.h, fill) for r in rects]
