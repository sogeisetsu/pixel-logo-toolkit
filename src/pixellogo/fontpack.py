"""多语言字体包的按需下载。

随包只分发中文简体（zh-hans）；繁体、日文、韩文在首次需要时下载到
``~/.pixellogo/fonts``（可用 ``PIXELLOGO_FONT_DIR`` 覆盖），避免仓库体积膨胀。

不同语言可能来自不同上游：繁中 / 日文用 Ark Pixel（含汉字与假名），
韩文用 Galmuri（Ark Pixel 的 ko 版并不含谚文）。
"""
from __future__ import annotations

import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from pixellogo import fonts, i18n

CHUNK = 256 * 1024


class FontPackError(RuntimeError):
    """字体包下载或安装失败。"""


def download_url(variant: fonts.Variant, mirror: str | None = None) -> str:
    """镜像优先：``PIXELLOGO_FONT_MIRROR`` 作为目录前缀，文件名沿用上游。"""
    base = mirror or os.environ.get("PIXELLOGO_FONT_MIRROR")
    if base:
        return f"{base.rstrip('/')}/{variant.archive}"
    return variant.url


def install(lang: str, log=print, timeout: int = 180) -> Path:
    """下载并安装某个语言变体，返回字体文件路径。"""
    key = fonts.normalize_lang(lang)
    variant = fonts.CJK_VARIANTS[key]

    for candidate in (fonts.FONT_DIR / variant.filename,
                      fonts.font_cache_dir() / variant.filename):
        if candidate.is_file():
            log(i18n.t("pack.exists", key=key, path=candidate))
            return candidate

    target_dir = fonts.font_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    url = download_url(variant)
    log(i18n.t("pack.downloading", key=key, label=variant.label, url=url))

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
                        log(f"\r  {read * 100 // total:3d}%  "
                            f"{read // 1048576}MB / {total // 1048576}MB", end="")
            if total:
                log("")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FontPackError(i18n.t("pack.download.failed", error=exc)) from None

        try:
            with zipfile.ZipFile(archive) as bundle:
                if variant.member not in bundle.namelist():
                    raise FontPackError(i18n.t("pack.member.missing", member=variant.member))
                with bundle.open(variant.member) as src:
                    destination = target_dir / variant.filename
                    with open(destination, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile:
            raise FontPackError(i18n.t("pack.zip.invalid")) from None

    if destination.stat().st_size < 1_000_000:
        destination.unlink(missing_ok=True)
        raise FontPackError(i18n.t("pack.file.small"))

    log(i18n.t("pack.installed", path=destination))
    return destination
