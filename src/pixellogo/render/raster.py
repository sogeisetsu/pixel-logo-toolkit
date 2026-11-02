"""PNG 后端：用 Pillow 直接填充整数矩形，不经过任何缩放滤波。"""
from __future__ import annotations

from PIL import Image, ImageDraw

from pixellogo.scene import Scene


def to_image(scene: Scene, scale: int = 1, mode: str = "RGB") -> Image.Image:
    image = Image.new(mode, (scene.width * scale, scene.height * scale), scene.background)
    draw = ImageDraw.Draw(image)
    for rect in scene.rects:
        x0 = rect.x * scale
        y0 = rect.y * scale
        x1 = x0 + rect.w * scale - 1
        y1 = y0 + rect.h * scale - 1
        draw.rectangle([x0, y0, x1, y1], fill=rect.fill)
    return image
