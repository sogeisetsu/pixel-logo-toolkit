"""画布模式：尺寸、默认排版走向与装饰默认值。

模式名用语义化单词（poster / card / banner / slide / square），不暴露比例数字；
比例本身只是结果，不是名字。旧的比例写法保留为别名，避免破坏已有配置。

尺寸以「逻辑像素」定义，输出时统一乘 ``scale``（默认 2），
因此 540×720 逻辑 = 1080×1440 输出。
"""
from __future__ import annotations

from dataclasses import dataclass

from pixellogo import i18n


@dataclass(frozen=True)
class Mode:
    key: str
    label: str
    width: int
    height: int
    scale: int = 2
    #: center | top
    vertical: str = "center"
    #: left | center
    align: str = "left"
    #: 文本可用宽度占内容区宽度的比例
    text_ratio: float = 1.0
    #: 标题初始字号相对画布高度的比例（随后按可用宽度自动收缩/放大）
    title_ratio: float = 0.24
    #: 默认装饰图形：none | blocks
    motif: str = "none"

    def label_for(self) -> str:
        """当前语言的画布说明；``label`` 保留英文原文作为兜底。"""
        key = f"mode.{self.key}"
        text = i18n.t(key, w=self.width, h=self.height)
        return self.label if text == key else text

    @property
    def ratio(self) -> str:
        """比例的文字形式，仅供参考展示。"""
        from math import gcd

        divisor = gcd(self.width, self.height) or 1
        return f"{self.width // divisor}:{self.height // divisor}"

    @property
    def output_size(self) -> tuple[int, int]:
        return self.width * self.scale, self.height * self.scale


MODES: dict[str, Mode] = {
    "poster": Mode(
        key="poster",
        label="Portrait poster (Xiaohongshu cover)",
        width=540,
        height=720,
        vertical="center",
        align="center",
        text_ratio=1.0,
        title_ratio=0.235,
    ),
    "card": Mode(
        key="card",
        label="Landscape card (article header / slides)",
        width=720,
        height=540,
        vertical="center",
        text_ratio=0.94,
        title_ratio=0.26,
    ),
    "banner": Mode(
        key="banner",
        label="Repository banner (GitHub preview)",
        width=640,
        height=320,
        vertical="center",
        text_ratio=0.72,
        title_ratio=0.30,
        motif="blocks",
    ),
    "slide": Mode(
        key="slide",
        label="Widescreen slide (16:9)",
        width=960,
        height=540,
        vertical="center",
        text_ratio=0.86,
        title_ratio=0.27,
    ),
    "square": Mode(
        key="square",
        label="Square image (social avatar / grid)",
        width=540,
        height=540,
        vertical="center",
        align="center",
        text_ratio=0.92,
        title_ratio=0.22,
    ),
}

ALIASES = {
    # 旧名（1.x 之前按比例命名）
    "xhs": "poster",
    "xiaohongshu": "poster",
    "red": "poster",
    "redbook": "poster",
    "3:4": "poster",
    "3x4": "poster",
    "4:3": "card",
    "4x3": "card",
    "landscape": "card",
    "og": "banner",
    "github": "banner",
    "repo": "banner",
    "social": "banner",
    "open-graph": "banner",
    "2:1": "banner",
    "2x1": "banner",
    "16:9": "slide",
    "16x9": "slide",
    "wide": "slide",
    "widescreen": "slide",
    "1:1": "square",
    "1x1": "square",
    "avatar": "square",
    "portrait": "poster",
    "story": "poster",
}

DEFAULT_MODE = "poster"


def get_mode(key: str) -> Mode:
    normalized = ALIASES.get(key.strip().lower(), key.strip().lower())
    try:
        return MODES[normalized]
    except KeyError:
        raise ValueError(i18n.t("mode.unknown", key=key, known=i18n.join(MODES))) from None


def custom_mode(width: int, height: int, scale: int = 2) -> Mode:
    if width < 64 or height < 64:
        raise ValueError(i18n.t("mode.too_small"))
    ratio = width / height
    return Mode(
        key="custom",
        label=f"Custom {width}×{height}",
        width=width,
        height=height,
        scale=scale,
        vertical="center" if ratio < 1 else "top",
        text_ratio=1.0,
        title_ratio=0.24,
    )


def list_modes() -> list[Mode]:
    return list(MODES.values())
