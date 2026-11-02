"""画布模式：画布尺寸、默认排版走向、装饰默认值。

尺寸以「逻辑像素」定义，输出时统一乘 ``scale``（默认 2），
因此 540×720 逻辑 = 1080×1440 输出，恰好是小红书封面的 3:4。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    key: str
    label: str
    width: int
    height: int
    scale: int = 2
    #: center | top
    vertical: str = "center"
    #: 文本可用宽度占内容区宽度的比例
    text_ratio: float = 1.0
    #: 标题初始字号相对画布高度的比例（随后按可用宽度自动收缩）
    title_ratio: float = 0.24
    #: 默认装饰图形：none | blocks
    motif: str = "none"

    @property
    def output_size(self) -> tuple[int, int]:
        return self.width * self.scale, self.height * self.scale


MODES: dict[str, Mode] = {
    "xhs": Mode(
        key="xhs",
        label="小红书竖版封面 3:4（1080×1440）",
        width=540,
        height=720,
        vertical="center",
        text_ratio=1.0,
        title_ratio=0.235,
    ),
    "4:3": Mode(
        key="4:3",
        label="横版 4:3（1440×1080）",
        width=720,
        height=540,
        vertical="center",
        text_ratio=0.94,
        title_ratio=0.26,
    ),
    "og": Mode(
        key="og",
        label="GitHub 仓库预览图 2:1（1280×640）",
        width=640,
        height=320,
        vertical="center",
        text_ratio=0.72,
        title_ratio=0.30,
        motif="blocks",
    ),
}

ALIASES = {
    "xiaohongshu": "xhs",
    "red": "xhs",
    "redbook": "xhs",
    "4x3": "4:3",
    "landscape": "4:3",
    "github": "og",
    "repo": "og",
    "social": "og",
    "open-graph": "og",
}

DEFAULT_MODE = "xhs"


def get_mode(key: str) -> Mode:
    normalized = ALIASES.get(key.strip().lower(), key.strip().lower())
    try:
        return MODES[normalized]
    except KeyError:
        known = "、".join(MODES)
        raise ValueError(f"未知画布模式 {key!r}；可用：{known}") from None


def custom_mode(width: int, height: int, scale: int = 2) -> Mode:
    if width < 64 or height < 64:
        raise ValueError("自定义画布宽高都必须 ≥ 64")
    ratio = width / height
    return Mode(
        key="custom",
        label=f"自定义 {width}×{height}",
        width=width,
        height=height,
        scale=scale,
        vertical="center" if ratio < 1 else "top",
        text_ratio=1.0,
        title_ratio=0.24,
    )


def list_modes() -> list[Mode]:
    return list(MODES.values())
