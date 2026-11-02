"""多语言字体包的按需下载。

随包只分发中文简体（zh-hans）；繁体、日文、韩文在首次需要时下载到
``~/.pixellogo/fonts``（可用 ``PIXELLOGO_FONT_DIR`` 覆盖），避免仓库体积膨胀。
"""
from __future__ import annotations

import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from pixellogo import fonts

#: 固定版本，避免上游发布新版本后字形突然变化
RELEASE_TAG = "2026.10.25"
ASSET_NAME = f"ark-pixel-font-12px-proportional-ttf-v{RELEASE_TAG}.zip"
DEFAULT_BASE_URL = (
    f"https://github.com/TakWolf/ark-pixel-font/releases/download/{RELEASE_TAG}"
)

CHUNK = 256 * 1024


class FontPackError(RuntimeError):
    """字体包下载或安装失败。"""


def download_url(base_url: str | None = None) -> str:
    """允许用 PIXELLOGO_FONT_MIRROR 指定镜像前缀。"""
    base = base_url or os.environ.get("PIXELLOGO_FONT_MIRROR") or DEFAULT_BASE_URL
    return f"{base.rstrip('/')}/{ASSET_NAME}"


def install(lang: str, log=print, timeout: int = 120) -> Path:
    """下载并安装某个语言变体，返回字体文件路径。"""
    key = fonts.normalize_lang(lang)
    filename = fonts.CJK_VARIANTS[key][0]

    for candidate in (fonts.FONT_DIR / filename, fonts.font_cache_dir() / filename):
        if candidate.is_file():
            log(f"{key} 字体已存在：{candidate}")
            return candidate

    target_dir = fonts.font_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_member = fonts.CJK_VARIANTS[key][1]
    url = download_url()
    log(f"下载 {key} 字体包…\n  {url}")

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "font.zip"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response, \
                    open(archive, "wb") as handle:
                total = int(response.headers.get("Content-Length") or 0)
                read = 0
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
                    read += len(chunk)
                    if total:
                        log(f"\r  {read * 100 // total:3d}%  {read // 1048576}MB / {total // 1048576}MB",
                            end="")
            if total:
                log("")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FontPackError(
                f"下载失败：{exc}\n"
                f"可设置 PIXELLOGO_FONT_MIRROR 指向镜像后重试。"
            ) from None

        try:
            with zipfile.ZipFile(archive) as bundle:
                if archive_member not in bundle.namelist():
                    raise FontPackError(f"字体包内没有 {archive_member}")
                with bundle.open(archive_member) as src:
                    destination = target_dir / filename
                    with open(destination, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile:
            raise FontPackError("下载到的文件不是有效的 zip，可能被网络代理拦截") from None

    if destination.stat().st_size < 1_000_000:
        destination.unlink(missing_ok=True)
        raise FontPackError("字体文件异常（体积过小），已删除，请重试")

    log(f"已安装：{destination}")
    return destination
