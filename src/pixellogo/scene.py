"""图元模型：所有输出都由整数坐标的矩形构成。

SVG 与 PNG 两个后端消费同一份 ``Scene``，因此两种格式在几何上完全一致。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Rect:
    """一个整数坐标的纯色矩形。"""

    x: int
    y: int
    w: int
    h: int
    fill: str

    def scaled(self, factor: int) -> "Rect":
        return Rect(self.x * factor, self.y * factor, self.w * factor, self.h * factor, self.fill)


@dataclass
class Scene:
    """一帧画面的全部几何信息（尚未放大）。"""

    width: int
    height: int
    background: str
    rects: list[Rect] = field(default_factory=list)

    def add(self, rect: Rect) -> None:
        if rect.w <= 0 or rect.h <= 0:
            return
        self.rects.append(rect)

    def extend(self, rects: Iterable[Rect]) -> None:
        for rect in rects:
            self.add(rect)

    @property
    def colors(self) -> list[str]:
        """画面用到的颜色（底色在前，用于检查色板规模）。"""
        seen = [self.background]
        for rect in self.rects:
            if rect.fill not in seen:
                seen.append(rect.fill)
        return seen
