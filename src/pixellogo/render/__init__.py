"""渲染后端：同一份 ``Scene`` 输出 PNG 或 SVG。"""
from __future__ import annotations

from pathlib import Path

from pixellogo import i18n
from pixellogo.render.raster import to_image
from pixellogo.render.svg import to_svg

FORMATS = ("png", "svg")


def render(scene, scale: int = 2, fmt: str = "png"):
    """返回 PIL Image 或 SVG 字符串。"""
    fmt = fmt.lower()
    if fmt == "png":
        return to_image(scene, scale=scale)
    if fmt == "svg":
        return to_svg(scene, scale=scale)
    raise ValueError(i18n.t("render.format.unsupported", fmt=fmt, opts=i18n.join(FORMATS)))


def save(scene, path: str | Path, scale: int = 2) -> Path:
    """按扩展名决定格式并写盘。"""
    path = Path(path)
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in FORMATS:
        raise ValueError(i18n.t("render.format.suffix", name=path.name))
    path.parent.mkdir(parents=True, exist_ok=True)
    result = render(scene, scale=scale, fmt=suffix)
    if suffix == "png":
        result.save(path, "PNG", optimize=True)
    else:
        path.write_text(result, encoding="utf-8")
    return path


__all__ = ["FORMATS", "render", "save", "to_image", "to_svg"]
