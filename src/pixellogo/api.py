"""Python API：不经过命令行也能出图。

参数键与 JSONC 配置文件完全一致，因此「配置里能写的」在这里都能写：

    from pixellogo import render

    render(title="REA", subtitle=["REVERSE ENGINEER"], mode="banner", out="out/")

需要中间产物（几何或位图）时用 :func:`make_scene` / :func:`make_image`。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from pixellogo import config as config_mod
from pixellogo.layout import build_scene
from pixellogo.paths import targets as build_targets
from pixellogo.paths import unique_paths
from pixellogo.render import save as save_scene
from pixellogo.render import to_image, to_svg
from pixellogo.scene import Scene


def _settings(options: dict[str, Any]) -> config_mod.Settings:
    cleaned = {key: value for key, value in options.items() if value is not None}
    return config_mod.resolve(cleaned, {})


def make_scene(**options: Any) -> Scene:
    """只做排版，返回未缩放的几何场景。"""
    return build_scene(_settings(options).design)


def make_image(**options: Any) -> Image.Image:
    """返回 Pillow 位图（已按 scale 放大）。"""
    settings = _settings(options)
    return to_image(build_scene(settings.design), scale=settings.scale)


def to_svg_text(**options: Any) -> str:
    """返回 SVG 源码字符串。"""
    settings = _settings(options)
    return to_svg(build_scene(settings.design), scale=settings.scale)


def render(**options: Any) -> list[Path]:
    """渲染并写盘，返回生成的文件路径。

    ``out`` 传目录按 ``<标题>-<模式>`` 命名，传文件名则按扩展名决定格式；
    ``format`` 可选 ``"png"`` / ``"svg"`` / ``"both"``。
    """
    settings = _settings(options)
    scene = build_scene(settings.design)
    paths = build_targets(settings.out, settings.design.title,
                          settings.mode_key, settings.formats)
    paths = unique_paths(paths, set())
    return [save_scene(scene, path, scale=settings.scale) for path in paths]


def render_many(items: list[dict[str, Any]], out: str = "out", format: str | None = None) -> list[list[Path]]:
    """批量渲染：每项是一份配置，``out`` 与 ``format`` 对所有项生效。"""
    results = []
    used: set[Path] = set()
    for item in items:
        options = dict(item)
        options["out"] = out
        if format:
            options["format"] = format
        settings = _settings(options)
        scene = build_scene(settings.design)
        paths = unique_paths(build_targets(settings.out, settings.design.title,
                                           settings.mode_key, settings.formats), used)
        results.append([save_scene(scene, path, scale=settings.scale) for path in paths])
    return results


__all__ = ["make_image", "make_scene", "render", "render_many", "to_svg_text"]
