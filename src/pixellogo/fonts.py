"""字体注册、路径解析与字形覆盖检测。

内置字体全部以包资源形式随包分发，安装后无需联网；也可以通过
``--font-title /path/to/font.ttf`` 指向任意本地字体。

字形覆盖通过直接解析 TTF 的 ``cmap`` 表得到（只依赖标准库）。这样在
中英混排时可以逐字选择回退字体，而不依赖 Pillow 对缺字的处理方式。
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
FONT_DIR = ASSETS / "fonts"
LICENSE_DIR = ASSETS / "licenses"


@dataclass(frozen=True)
class FontSpec:
    """一款内置字体的元信息。"""

    key: str
    filename: str
    label: str
    coverage: str  # latin | cjk
    license_file: str

    @property
    def path(self) -> Path:
        return FONT_DIR / self.filename


BUILTIN_FONTS: dict[str, FontSpec] = {
    "press-start-2p": FontSpec(
        key="press-start-2p",
        filename="PressStart2P.ttf",
        label="Press Start 2P",
        coverage="latin",
        license_file="OFL-PressStart2P.txt",
    ),
    "silkscreen": FontSpec(
        key="silkscreen",
        filename="Silkscreen.ttf",
        label="Silkscreen",
        coverage="latin",
        license_file="OFL-Silkscreen.txt",
    ),
    "pixelify": FontSpec(
        key="pixelify",
        filename="PixelifySans.ttf",
        label="Pixelify Sans",
        coverage="latin",
        license_file="OFL-PixelifySans.txt",
    ),
    "ark-pixel": FontSpec(
        key="ark-pixel",
        filename="ArkPixel-zh-hans.ttf",
        label="Ark Pixel 12px Proportional (zh-hans)",
        coverage="cjk",
        license_file="OFL-ArkPixel12pxProportional.txt",
    ),
}

DEFAULT_CJK_FALLBACK = "ark-pixel"

ARK_TAG = "2026.10.25"
ARK_ARCHIVE = f"ark-pixel-font-12px-proportional-ttf-v{ARK_TAG}.zip"
ARK_URL = ("https://github.com/TakWolf/ark-pixel-font/releases/download/"
           f"{ARK_TAG}/{ARK_ARCHIVE}")

GALMURI_TAG = "v2.40.4"
GALMURI_ARCHIVE = f"Galmuri-{GALMURI_TAG}.zip"
GALMURI_URL = ("https://github.com/quiple/galmuri/releases/download/"
               f"{GALMURI_TAG}/{GALMURI_ARCHIVE}")


@dataclass(frozen=True)
class Variant:
    """一个语言字形变体的来源信息。"""

    filename: str    # 落地后的文件名
    member: str      # 压缩包内路径
    archive: str     # 压缩包文件名
    url: str         # 下载地址
    label: str       # 展示名


#: 中日韩字形变体。注意：Ark Pixel 的 ko 版并不含谚文，韩语改用 Galmuri。
CJK_VARIANTS: dict[str, Variant] = {
    "zh-hans": Variant("ArkPixel-zh-hans.ttf", "ark-pixel-12px-proportional-zh_hans.ttf",
                       ARK_ARCHIVE, ARK_URL, "Ark Pixel 12px (zh-hans)"),
    "zh-hant": Variant("ArkPixel-zh-hant.ttf", "ark-pixel-12px-proportional-zh_hant.ttf",
                       ARK_ARCHIVE, ARK_URL, "Ark Pixel 12px (zh-hant)"),
    "ja": Variant("ArkPixel-ja.ttf", "ark-pixel-12px-proportional-ja.ttf",
                  ARK_ARCHIVE, ARK_URL, "Ark Pixel 12px (ja)"),
    "ko": Variant("Galmuri11.ttf", "Galmuri11.ttf",
                  GALMURI_ARCHIVE, GALMURI_URL, "Galmuri 11px (ko)"),
}

CJK_ALIASES = {
    "zh": "zh-hans",
    "zh-cn": "zh-hans",
    "zh_hans": "zh-hans",
    "zh-tw": "zh-hant",
    "zh-hk": "zh-hant",
    "zh_hant": "zh-hant",
    "jp": "ja",
    "ja-jp": "ja",
    "kr": "ko",
    "ko-kr": "ko",
}

#: 随包分发的变体，其余从 GitHub Release 按需下载
BUNDLED_VARIANTS = {"zh-hans"}

DEFAULT_LANG = "zh-hans"


def font_cache_dir() -> Path:
    """用户字体目录，可用环境变量 PIXELLOGO_FONT_DIR 覆盖。"""
    override = os.environ.get("PIXELLOGO_FONT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".pixellogo" / "fonts"


def normalize_lang(lang: str) -> str:
    key = (lang or DEFAULT_LANG).strip().lower().replace("_", "-")
    key = CJK_ALIASES.get(key, key)
    if key not in CJK_VARIANTS:
        known = "、".join(CJK_VARIANTS)
        raise FontError(f"未知语言 {lang!r}；可用：{known}")
    return key


def cjk_font_path(lang: str = DEFAULT_LANG) -> str:
    """返回某语言变体的字体路径；未安装时抛出带安装提示的错误。"""
    key = normalize_lang(lang)
    filename = CJK_VARIANTS[key].filename
    bundled = FONT_DIR / filename
    if bundled.is_file():
        return str(bundled)
    cached = font_cache_dir() / filename
    if cached.is_file():
        return str(cached)
    raise FontError(
        f"未安装 {key} 字体。运行 `pixellogo fonts install {key}` 下载后重试，"
        f"或改用 --lang zh-hans"
    )


def variant_status() -> list[tuple[str, str, str]]:
    """列出各语言变体的 (语言, 状态, 字体名)：bundled / installed / missing。"""
    rows: list[tuple[str, str, str]] = []
    for key, variant in CJK_VARIANTS.items():
        if (FONT_DIR / variant.filename).is_file():
            rows.append((key, "bundled", variant.label))
        elif (font_cache_dir() / variant.filename).is_file():
            rows.append((key, "installed", variant.label))
        else:
            rows.append((key, "missing", variant.label))
    return rows


class FontError(ValueError):
    """字体解析失败。"""


def font_path(name_or_path: str) -> str:
    """把字体键名或文件路径解析成实际路径。"""
    if not name_or_path:
        raise FontError("字体名为空")
    spec = BUILTIN_FONTS.get(name_or_path)
    if spec is not None:
        if not spec.path.exists():
            raise FontError(f"内置字体缺失：{spec.path}")
        return str(spec.path)
    candidate = Path(name_or_path).expanduser()
    if candidate.is_file():
        return str(candidate)
    known = "、".join(sorted(BUILTIN_FONTS))
    raise FontError(f"未知字体 {name_or_path!r}；可用内置字体：{known}；或传入 .ttf 路径")


def _read_table_offsets(data: bytes) -> dict[bytes, tuple[int, int]]:
    if len(data) < 12:
        raise FontError("不是有效的字体文件")
    tag = data[:4]
    if tag not in (b"\x00\x01\x00\x00", b"true", b"OTTO", b"ttcf"):
        raise FontError("不是有效的 TrueType/OpenType 字体")
    num_tables = struct.unpack(">H", data[4:6])[0]
    tables: dict[bytes, tuple[int, int]] = {}
    for index in range(num_tables):
        record = 12 + index * 16
        if record + 16 > len(data):
            break
        name = data[record : record + 4]
        offset, length = struct.unpack(">II", data[record + 8 : record + 16])
        tables[name] = (offset, length)
    return tables


def _parse_cmap_format4(data: bytes, start: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    seg_x2 = struct.unpack(">H", data[start + 6 : start + 8])[0]
    seg_count = seg_x2 // 2
    end_base = start + 14
    start_base = end_base + seg_x2 + 2
    for index in range(seg_count):
        end = struct.unpack(">H", data[end_base + index * 2 : end_base + index * 2 + 2])[0]
        begin = struct.unpack(">H", data[start_base + index * 2 : start_base + index * 2 + 2])[0]
        if end == 0xFFFF and begin == 0xFFFF:
            continue
        if end >= begin:
            ranges.append((begin, end))
    return ranges


def _parse_cmap_format12(data: bytes, start: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    n_groups = struct.unpack(">I", data[start + 12 : start + 16])[0]
    for index in range(n_groups):
        pos = start + 16 + index * 12
        begin, end, _glyph = struct.unpack(">III", data[pos : pos + 12])
        if end >= begin:
            ranges.append((begin, end))
    return ranges


@lru_cache(maxsize=32)
def _font_ranges(path: str) -> tuple[tuple[int, int], ...]:
    """字体覆盖的 Unicode 区间（有序、已合并），避免把每个码位都展开成集合。"""
    data = Path(path).read_bytes()
    tables = _read_table_offsets(data)
    if b"cmap" not in tables:
        raise FontError(f"字体缺少 cmap 表：{path}")
    cmap_offset = tables[b"cmap"][0]
    num_subtables = struct.unpack(">H", data[cmap_offset + 2 : cmap_offset + 4])[0]
    best: tuple[int, int, int] | None = None  # (优先级, 偏移, 格式)
    for index in range(num_subtables):
        record = cmap_offset + 4 + index * 8
        platform_id, encoding_id = struct.unpack(">HH", data[record : record + 4])
        # cmap 编码记录里的 offset 是相对 cmap 表起始的偏移
        sub_offset = cmap_offset + struct.unpack(">I", data[record + 4 : record + 8])[0]
        fmt = struct.unpack(">H", data[sub_offset : sub_offset + 2])[0]
        if fmt not in (4, 12):
            continue
        # 优先 UCS-4（format 12），其次 Windows BMP（format 4）
        priority = {12: 3, 4: 1}[fmt] + (1 if platform_id in (0, 3) else 0)
        if best is None or priority > best[0]:
            best = (priority, sub_offset, fmt)
    if best is None:
        raise FontError(f"字体没有可用的 Unicode cmap 子表：{path}")
    _, sub_offset, fmt = best
    raw = (_parse_cmap_format4(data, sub_offset) if fmt == 4
           else _parse_cmap_format12(data, sub_offset))
    merged: list[tuple[int, int]] = []
    for begin, end in sorted(raw):
        if merged and begin <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((begin, end))
    return tuple(merged)


def covers(font: str, char: str) -> bool:
    """该字体是否包含某个字符的字形。"""
    ranges = _font_ranges(font)
    codepoint = ord(char)
    low, high = 0, len(ranges) - 1
    while low <= high:
        mid = (low + high) // 2
        begin, end = ranges[mid]
        if codepoint < begin:
            high = mid - 1
        elif codepoint > end:
            low = mid + 1
        else:
            return True
    return False


def missing_chars(font: str, text: str) -> list[str]:
    """返回 text 中该字体缺失的、去重后的字符。"""
    ranges = _font_ranges(font)
    missing: list[str] = []
    for char in text:
        if char.isspace() or char in missing:
            continue
        if not covers(font, char):
            missing.append(char)
    return missing


def resolve_chain(primary: str, fallbacks: list[str] | None = None) -> list[str]:
    """将主字体与回退字体解析成一组实际路径（去重、保序）。"""
    chain = [font_path(primary)]
    for item in fallbacks or [DEFAULT_CJK_FALLBACK]:
        try:
            path = font_path(item)
        except FontError:
            continue
        if path not in chain:
            chain.append(path)
    return chain


def pick_unified(text: str, chain: list[str]) -> str:
    """为一整行文字挑选唯一字体：优先用能完整覆盖它的第一个字体。

    中英混排时整行统一字形，避免同一行里出现两种笔画粗细。
    """
    for path in chain:
        if not missing_chars(path, text):
            return path
    return chain[0]


def pick_per_char(char: str, chain: list[str]) -> str:
    """逐字挑选字体，找不到覆盖字体时退回主字体。"""
    for path in chain:
        if covers(path, char):
            return path
    return chain[0]


def list_fonts() -> list[FontSpec]:
    return [BUILTIN_FONTS[key] for key in BUILTIN_FONTS]
