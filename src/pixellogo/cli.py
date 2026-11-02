"""命令行入口。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pixellogo import __version__

PROG = "pixellogo"


def slugify(text: str, fallback: str = "pixellogo") -> str:
    """把标题变成安全的文件名片段（保留中日韩字符）。"""
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "-", text.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:60] or fallback


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="生成 8-bit / 复古终端风格的像素图（PNG / SVG）。",
        epilog='示例：pixellogo -t "REA" -s "REVERSE ENGINEER" -m xhs -o out/',
    )
    parser.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}")

    content = parser.add_argument_group("内容")
    content.add_argument("-t", "--title", help="主标题，支持 \\n 换行")
    content.add_argument("-s", "--subtitle", action="append", metavar="TEXT", help="副标题行，可重复")
    content.add_argument("-d", "--desc", action="append", metavar="TEXT", help="底部说明行，可重复")
    content.add_argument("-e", "--eyebrow", default="", metavar="TEXT", help="标题上方的小字标签")
    content.add_argument("--badge", default="", metavar="TEXT", help="右上角徽标文字")

    style = parser.add_argument_group("风格")
    style.add_argument("-p", "--preset", default=None, metavar="NAME",
                       help="风格预设，见 --list presets（默认 terminal）")
    style.add_argument("--bg", metavar="HEX", help="底色")
    style.add_argument("--fg", metavar="HEX", help="字色")
    style.add_argument("--primary", metavar="HEX", help="主色（标题）")
    style.add_argument("--accent", metavar="HEX", help="强调色（分隔线/徽标）")
    style.add_argument("--shadow-color", metavar="HEX", help="投影色")
    style.add_argument("--shadow-offset", type=int, default=None, metavar="N",
                       help="投影格数，0 关闭（默认 1）")
    style.add_argument("--title-size", type=int, metavar="PX", help="标题字号，缺省按画布自动适配")
    style.add_argument("--font-title", metavar="NAME|PATH", help="主标题字体")
    style.add_argument("--font-sub", metavar="NAME|PATH", help="副标题字体")
    style.add_argument("--font-body", metavar="NAME|PATH", help="说明文字字体")

    layout = parser.add_argument_group("排版")
    layout.add_argument("--align", choices=["auto", "left", "center"], default="auto", help="对齐方式")
    layout.add_argument("--vertical", choices=["auto", "top", "center"], default="auto", help="纵向锚定")
    layout.add_argument("--margin", type=float, metavar="RATIO", help="安全边距，相对画布短边（默认 0.06）")
    layout.add_argument("--divider", choices=["auto", "line", "dash", "block", "none"],
                        default="auto", help="分隔线样式")
    layout.add_argument("--divider-width", type=float, metavar="RATIO", help="分隔线宽度比（默认 0.42）")
    layout.add_argument("--motif", choices=["auto", "none", "blocks"], default="auto", help="装饰图形")

    out = parser.add_argument_group("输出")
    out.add_argument("-m", "--mode", default=None, metavar="MODE",
                     help="画布模式：xhs / 4:3 / og（默认 xhs）")
    out.add_argument("--size", metavar="WxH", help="自定义画布，如 1200x900")
    out.add_argument("--scale", type=int, default=None, metavar="N", help="输出放大倍数（默认 2）")
    out.add_argument("-o", "--out", default=None, metavar="PATH", help="输出文件或目录（默认 out/）")

    config_group = parser.add_argument_group("配置")
    config_group.add_argument("-c", "--config", metavar="PATH", help="JSONC 配置文件")
    config_group.add_argument("--set", action="append", metavar="KEY=VALUE",
                              help="按点路径覆盖配置，如 colors.primary=#FF3D81，可重复")
    config_group.add_argument("--dry-run", action="store_true", help="只打印合并后的配置，不渲染")

    misc = parser.add_argument_group("其他")
    misc.add_argument("--list", choices=["presets", "modes", "fonts"], help="列出可选项后退出")
    return parser


def _cmd_list(kind: str) -> int:
    from pixellogo import fonts, modes, presets

    if kind == "presets":
        for preset in presets.list_presets():
            print(f"{preset.key:<10} {preset.label:<16} 底色 {preset.bg}  主色 {preset.primary}")
    elif kind == "modes":
        for mode in modes.list_modes():
            w, h = mode.output_size
            print(f"{mode.key:<8} {mode.label:<34} 输出 {w}×{h}")
    else:
        for spec in fonts.list_fonts():
            print(f"{spec.key:<16} {spec.label:<42} {spec.coverage}")
    return 0


def _resolve_target(out: str, title: str, mode_key: str) -> Path:
    path = Path(out)
    if path.suffix.lower() in (".png", ".svg"):
        return path
    return path / f"{slugify(title)}-{mode_key.replace(':', 'x')}.png"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        return _cmd_list(args.list)

    from pixellogo import config as config_mod
    from pixellogo import jsonc
    from pixellogo.layout import build_scene
    from pixellogo.render import save

    try:
        file_data = jsonc.load(args.config) if args.config else None
        cli_data = config_mod.cli_to_config(args)
        for item in args.set or []:
            key, sep, value = item.partition("=")
            if not sep or not key.strip():
                raise config_mod.ConfigError(f"--set 需要 KEY=VALUE 形式，收到 {item!r}")
            config_mod.set_path(cli_data, key.strip(), config_mod.coerce(value))
        settings = config_mod.resolve(file_data, cli_data)
    except (ValueError, OSError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 2

    for warning in settings.warnings:
        print(f"{PROG}: 提示：{warning}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(settings.describe(), ensure_ascii=False, indent=2))
        return 0

    try:
        scene = build_scene(settings.design)
        target = _resolve_target(settings.out, settings.design.title, settings.mode_key)
        save(scene, target, scale=settings.scale)
    except (ValueError, OSError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 2

    print(f"{target}  ({scene.width * settings.scale}×{scene.height * settings.scale})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
