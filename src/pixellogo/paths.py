"""输出路径规则：命令行与 Python API 共用，保证两边命名一致。"""
from __future__ import annotations

import re
from pathlib import Path


def slugify(text: str, fallback: str = "pixellogo") -> str:
    """把标题变成安全的文件名片段（保留中日韩字符）。"""
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "-", text.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:60] or fallback


def targets(out: str | Path, title: str, mode_key: str, formats: list[str]) -> list[Path]:
    """按输出目标与格式列表算出落地路径。

    ``out`` 是文件（.png/.svg）时按其主干换扩展名；是目录时按 ``<标题>-<模式>`` 命名。
    """
    path = Path(out)
    if path.suffix.lower() in (".png", ".svg"):
        stem = path.with_suffix("")
        return [stem.with_suffix("." + fmt) for fmt in formats]
    name = f"{slugify(title)}-{mode_key.replace(':', 'x')}"
    return [path / f"{name}.{fmt}" for fmt in formats]


def unique_paths(paths: list[Path], used: set[Path]) -> list[Path]:
    """批量出图时避免同名覆盖。"""
    result: list[Path] = []
    for path in paths:
        candidate = path
        index = 2
        while candidate in used:
            candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
            index += 1
        used.add(candidate)
        result.append(candidate)
    return result
