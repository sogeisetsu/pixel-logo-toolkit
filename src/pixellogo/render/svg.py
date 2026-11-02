"""SVG 后端：把图元序列化成完全自包含的矢量文件。"""
from __future__ import annotations

from pixellogo.scene import Scene

HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
    'viewBox="0 0 {w} {h}" shape-rendering="crispEdges">'
)


def rect_svg(rect_x: int, rect_y: int, rect_w: int, rect_h: int, fill: str) -> str:
    return (
        f'<rect x="{int(rect_x)}" y="{int(rect_y)}" width="{int(rect_w)}" '
        f'height="{int(rect_h)}" fill="{fill}"/>'
    )


def to_svg(scene: Scene, scale: int = 1) -> str:
    """按整数倍放大输出；``scale`` 只影响 width/height 与 rect 尺寸。"""
    width = scene.width * scale
    height = scene.height * scale
    parts = [HEADER.format(w=width, h=height)]
    parts.append(rect_svg(0, 0, width, height, scene.background))
    for rect in scene.rects:
        parts.append(rect_svg(rect.x * scale, rect.y * scale, rect.w * scale, rect.h * scale, rect.fill))
    parts.append("</svg>")
    return "".join(parts)
