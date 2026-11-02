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
}

DEFAULT_PRESET = "terminal"


def get_preset(key: str) -> Preset:
    try:
        return PRESETS[key]
    except KeyError:
        known = "、".join(PRESETS)
        raise ValueError(f"未知风格预设 {key!r}；可用：{known}") from None


def list_presets() -> list[Preset]:
    return list(PRESETS.values())
