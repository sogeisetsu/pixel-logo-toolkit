"""风格预设：配色 + 字体组合 + 投影强度 + 装饰样式。

配色沿用 ``docs/style-spec.md`` 的实测色板；每套预设保持
「中性底 + 高饱和主色 + 唯一强调色」的分工。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    bg: str
    fg: str
    primary: str
    accent: str
    shadow: str
    title_font: str
    sub_font: str
    body_font: str
    #: 投影偏移相对字号的比例（0 表示不画投影）
    shadow_ratio: float = 0.06
    #: 分隔线样式：line / dash / block / none
    divider: str = "line"
    #: 深色底需要更亮的字色，用于对比度自检
    dark: bool = False


PRESETS: dict[str, Preset] = {
    "terminal": Preset(
        key="terminal",
        label="复古终端（参考原味）",
        bg="#EEF1F6",
        fg="#1F1F1F",
        primary="#02ADFB",
        accent="#FF6104",
        shadow="#2B3444",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
    ),
    "cyber": Preset(
        key="cyber",
        label="暗夜赛博",
        bg="#0D1117",
        fg="#E6EDF3",
        primary="#00E5A0",
        accent="#FF3D81",
        shadow="#05070C",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        dark=True,
    ),
    "arcade": Preset(
        key="arcade",
        label="复古街机",
        bg="#1B1F27",
        fg="#F5F5F5",
        primary="#FFD200",
        accent="#FF5F1F",
        shadow="#000000",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.08,
        dark=True,
    ),
    "candy": Preset(
        key="candy",
        label="柔和糖果",
        bg="#FFF5F7",
        fg="#3D2B33",
        primary="#FF7EB6",
        accent="#4ECDC4",
        shadow="#8A5A72",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.05,
    ),
    "minimal": Preset(
        key="minimal",
        label="极简专业",
        bg="#F8FAFC",
        fg="#0F172A",
        primary="#2563EB",
        accent="#F97316",
        shadow="#1E293B",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.04,
        divider="line",
    ),
    "noir": Preset(
        key="noir",
        label="黑白纪实",
        bg="#F4F4F5",
        fg="#18181B",
        primary="#18181B",
        accent="#E11D48",
        shadow="#A1A1AA",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.05,
        divider="line",
    ),
    "forest": Preset(
        key="forest",
        label="森林苔绿",
        bg="#F0F4EF",
        fg="#1C2B21",
        primary="#2F6B3C",
        accent="#D97706",
        shadow="#22382A",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.05,
        divider="line",
    ),
    "sunset": Preset(
        key="sunset",
        label="黄昏日落",
        bg="#2B1B2F",
        fg="#FFE8D6",
        primary="#FF8A3D",
        accent="#FFD166",
        shadow="#14060F",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.07,
        divider="line",
        dark=True,
    ),
    "ocean": Preset(
        key="ocean",
        label="深海青蓝",
        bg="#E8F1F5",
        fg="#0B2E3F",
        primary="#0077B6",
        accent="#2A9D8F",
        shadow="#06324A",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.05,
        divider="line",
    ),
    "paper": Preset(
        key="paper",
        label="纸本手账",
        bg="#F5EEE1",
        fg="#33291D",
        primary="#8C3B2E",
        accent="#C9822E",
        shadow="#8A7457",
        title_font="press-start-2p",
        sub_font="silkscreen",
        body_font="pixelify",
        shadow_ratio=0.045,
        divider="dash",
    ),
}

DEFAULT_PRESET = "terminal"


def _luminance(color: str) -> float:
    """WCAG 相对亮度，用于自检字色与底色的对比度。"""
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    channels = []
    for index in (0, 2, 4):
        raw = int(value[index:index + 2], 16) / 255
        channels.append(raw / 12.92 if raw <= 0.03928 else ((raw + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """两个色值的对比度（1–21）。"""
    a, b = _luminance(first), _luminance(second)
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


def get_preset(key: str) -> Preset:
    try:
        return PRESETS[key]
    except KeyError:
        known = "、".join(PRESETS)
        raise ValueError(f"未知风格预设 {key!r}；可用：{known}") from None


def list_presets() -> list[Preset]:
    return list(PRESETS.values())
