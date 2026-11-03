"""pixellogo —— 8-bit / 复古终端风格的像素图生成器。

渲染依赖 Pillow。缺少 Pillow 时本模块仍可导入（``--version`` / ``--help`` /
``--list`` 等纯查询命令照常可用），只有在真正取用渲染 API 时才会抛出带提示的
``ImportError``。
"""

__version__ = "0.3.0"

__all__ = [
    "__version__",
    "make_image",
    "make_scene",
    "render",
    "render_many",
    "to_svg_text",
]

try:
    from pixellogo.api import make_image, make_scene, render, render_many, to_svg_text
except ImportError as _exc:  # 几乎只会因为缺少 Pillow 走到这里
    _IMPORT_ERROR = _exc

    def __getattr__(name: str):
        if name in __all__:
            from pixellogo import i18n

            raise ImportError(i18n.t("error.pillow")) from _IMPORT_ERROR
        # 其余名字（含 i18n 这类子模块）走正常的属性/子模块查找
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

else:
    _IMPORT_ERROR = None
