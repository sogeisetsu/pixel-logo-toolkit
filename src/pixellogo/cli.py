"""命令行入口。

所有面向用户的文案都经 :mod:`pixellogo.i18n` 取用，默认跟随终端语言，
也可以用 ``--ui-lang`` 或 ``PIXELLOGO_UI_LANG`` 显式指定。
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from pixellogo import __version__
from pixellogo import i18n
from pixellogo.paths import targets as _targets
from pixellogo.paths import unique_paths as _unique

PROG = "pixellogo"

UI_LANG_FLAG = "--ui-lang"
UI_LANG_CHOICES = ("auto", "en", "zh")


class _Parser(argparse.ArgumentParser):
    """把 usage 前缀与常见报错换成当前语言的 argparse。"""

    @staticmethod
    def _localize(text: str) -> str:
        if i18n.is_chinese() and text.startswith("usage:"):
            return "用法:" + text[len("usage:"):]
        return text

    def format_usage(self) -> str:
        return self._localize(super().format_usage())

    def format_help(self) -> str:
        return self._localize(super().format_help())

    def error(self, message: str):  # noqa: D102 - 覆盖 argparse 行为
        self.print_usage(sys.stderr)
        self.exit(2, i18n.t("cli.error", prog=self.prog,
                            message=i18n.translate_argparse_error(message)) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=PROG,
        description=i18n.t("cli.description"),
        epilog=i18n.t("cli.epilog"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    general = parser.add_argument_group(i18n.t("cli.group.general"))
    general.add_argument("-h", "--help", action="help", help=i18n.t("cli.arg.help"))
    general.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}",
                         help=i18n.t("cli.arg.version"))
    general.add_argument(UI_LANG_FLAG, choices=list(UI_LANG_CHOICES), default="auto",
                         metavar="LANG", help=i18n.t("cli.arg.ui_lang"))

    content = parser.add_argument_group(i18n.t("cli.group.content"))
    content.add_argument("-t", "--title", help=i18n.t("cli.arg.title"))
    content.add_argument("-s", "--subtitle", action="append", metavar="TEXT",
                         help=i18n.t("cli.arg.subtitle"))
    content.add_argument("-d", "--desc", action="append", metavar="TEXT",
                         help=i18n.t("cli.arg.desc"))
    content.add_argument("-e", "--eyebrow", default="", metavar="TEXT",
                         help=i18n.t("cli.arg.eyebrow"))
    content.add_argument("--badge", default="", metavar="TEXT", help=i18n.t("cli.arg.badge"))

    style = parser.add_argument_group(i18n.t("cli.group.style"))
    style.add_argument("-p", "--preset", default=None, metavar="NAME",
                       help=i18n.t("cli.arg.preset"))
    style.add_argument("--bg", metavar="HEX", help=i18n.t("cli.arg.bg"))
    style.add_argument("--fg", metavar="HEX", help=i18n.t("cli.arg.fg"))
    style.add_argument("--primary", metavar="HEX", help=i18n.t("cli.arg.primary"))
    style.add_argument("--accent", metavar="HEX", help=i18n.t("cli.arg.accent"))
    style.add_argument("--shadow-color", metavar="HEX", help=i18n.t("cli.arg.shadow_color"))
    style.add_argument("--shadow-offset", type=int, default=None, metavar="N",
                       help=i18n.t("cli.arg.shadow_offset"))
    style.add_argument("--title-size", type=int, metavar="PX", help=i18n.t("cli.arg.title_size"))
    style.add_argument("--tracking", type=float, default=None, metavar="RATIO",
                       help=i18n.t("cli.arg.tracking"))
    style.add_argument("--leading", type=float, default=None, metavar="RATIO",
                       help=i18n.t("cli.arg.leading"))
    style.add_argument("--uppercase", action="store_true", help=i18n.t("cli.arg.uppercase"))
    style.add_argument("--lang", metavar="LANG", default=None, help=i18n.t("cli.arg.lang"))
    style.add_argument("--font-title", metavar="NAME|PATH", help=i18n.t("cli.arg.font_title"))
    style.add_argument("--font-sub", metavar="NAME|PATH", help=i18n.t("cli.arg.font_sub"))
    style.add_argument("--font-body", metavar="NAME|PATH", help=i18n.t("cli.arg.font_body"))

    layout = parser.add_argument_group(i18n.t("cli.group.layout"))
    layout.add_argument("--align", choices=["auto", "left", "center"], default="auto",
                        help=i18n.t("cli.arg.align"))
    layout.add_argument("--vertical", choices=["auto", "top", "center"], default="auto",
                        help=i18n.t("cli.arg.vertical"))
    layout.add_argument("--margin", type=float, metavar="RATIO", help=i18n.t("cli.arg.margin"))
    layout.add_argument("--divider", choices=["auto", "line", "dash", "block", "none"],
                        default="auto", help=i18n.t("cli.arg.divider"))
    layout.add_argument("--divider-width", type=float, metavar="RATIO",
                        help=i18n.t("cli.arg.divider_width"))
    layout.add_argument("--motif", choices=["auto", "none", "blocks"], default="auto",
                        help=i18n.t("cli.arg.motif"))
    layout.add_argument("--bg-pattern", choices=["none", "grid", "dots", "scanlines"], default=None,
                        help=i18n.t("cli.arg.bg_pattern"))
    layout.add_argument("--wrap", action=argparse.BooleanOptionalAction, default=None,
                        help=i18n.t("cli.arg.wrap"))

    out = parser.add_argument_group(i18n.t("cli.group.output"))
    out.add_argument("-m", "--mode", default=None, metavar="MODE", help=i18n.t("cli.arg.mode"))
    out.add_argument("--size", metavar="WxH", help=i18n.t("cli.arg.size"))
    out.add_argument("--scale", type=int, default=None, metavar="N", help=i18n.t("cli.arg.scale"))
    out.add_argument("-f", "--format", choices=["png", "svg", "both"], default=None,
                     help=i18n.t("cli.arg.format"))
    out.add_argument("-o", "--out", default=None, metavar="PATH", help=i18n.t("cli.arg.out"))

    config_group = parser.add_argument_group(i18n.t("cli.group.config"))
    config_group.add_argument("-c", "--config", metavar="PATH", help=i18n.t("cli.arg.config"))
    config_group.add_argument("--set", action="append", metavar="KEY=VALUE",
                              help=i18n.t("cli.arg.set"))
    config_group.add_argument("--dry-run", action="store_true", help=i18n.t("cli.arg.dry_run"))

    misc = parser.add_argument_group(i18n.t("cli.group.misc"))
    misc.add_argument("--json", action="store_true", help=i18n.t("cli.arg.json"))
    misc.add_argument("--open", action="store_true", help=i18n.t("cli.arg.open"))
    misc.add_argument("--list", choices=["presets", "modes", "fonts"],
                      help=i18n.t("cli.arg.list"))
    return parser


def _prescan_language(argv: list[str]) -> str:
    """在建立解析器之前确定语言，保证 ``-h`` / ``--list`` 也按同一语言输出。"""
    requested: str | None = None
    for index, token in enumerate(argv):
        if token == UI_LANG_FLAG and index + 1 < len(argv):
            requested = argv[index + 1]
        elif token.startswith(UI_LANG_FLAG + "="):
            requested = token.split("=", 1)[1]
    try:
        return i18n.set_language(requested)
    except ValueError:
        # 非法取值交给 argparse 报错，这里先按自动推断排版帮助
        return i18n.set_language("auto")


def _strip_ui_lang(argv: list[str]) -> list[str]:
    """去掉 ``--ui-lang`` 及其取值，便于把剩余参数交给子命令处理。

    孤立的 ``--ui-lang``（后面没跟值）会被保留，交给 argparse 报错。
    """
    cleaned: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == UI_LANG_FLAG:
            following = argv[index + 1] if index + 1 < len(argv) else None
            if following is not None and not following.startswith("-"):
                index += 2
                continue
            cleaned.append(token)
            index += 1
            continue
        if token.startswith(UI_LANG_FLAG + "="):
            index += 1
            continue
        cleaned.append(token)
        index += 1
    return cleaned


def _cmd_fonts(argv: list[str]) -> int:
    from pixellogo import fonts

    if not argv or argv[0] in ("list", "--list"):
        for key, status, label in fonts.variant_status():
            status_label = i18n.t(f"fonts.status.{status}")
            print(f"{key:<8} {i18n.pad(status_label, 16)} {label}")
        print("\n" + i18n.t("fonts.dir", path=fonts.font_cache_dir()))
        print(i18n.t("fonts.hint"))
        return 0

    if argv[0] == "install":
        if len(argv) < 2:
            print(i18n.t("fonts.need_lang", prog=PROG), file=sys.stderr)
            return 2
        from pixellogo import fontpack

        try:
            fontpack.install(argv[1])
        except (ValueError, RuntimeError) as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return 2
        return 0

    print(i18n.t("fonts.usage", prog=PROG), file=sys.stderr)
    return 2


def _cmd_list(kind: str) -> int:
    from pixellogo import fonts, modes, presets

    if kind == "presets":
        line = i18n.t("list.presets")
        for preset in presets.list_presets():
            ratio = presets.contrast_ratio(preset.fg, preset.bg)
            print(line.format(key=preset.key, label=i18n.pad(preset.label_for(), 26),
                              bg=preset.bg, primary=preset.primary,
                              accent=preset.accent, ratio=ratio))
    elif kind == "modes":
        line = i18n.t("list.modes")
        for mode in modes.list_modes():
            w, h = mode.output_size
            print(line.format(key=mode.key, ratio=mode.ratio,
                              label=i18n.pad(mode.label_for(), 42), w=w, h=h))
    else:
        line = i18n.t("list.fonts")
        for spec in fonts.list_fonts():
            print(line.format(key=spec.key, label=spec.label, coverage=spec.coverage))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _prescan_language(argv)

    parser = build_parser()
    # 子命令与 help 判定忽略 --ui-lang，这样「pixellogo --ui-lang en fonts」也成立
    stripped = _strip_ui_lang(argv)
    if not stripped:
        if argv:
            # 只给了 --ui-lang：先让 argparse 校验取值，再按裸执行处理
            parser.parse_args(argv)
        parser.print_help()
        return 0
    if stripped[0] in ("help", "--help-all"):
        parser.print_help()
        return 0
    if stripped[0] == "fonts":
        return _cmd_fonts(stripped[1:])

    args = parser.parse_args(argv)

    if args.list:
        return _cmd_list(args.list)

    try:
        from pixellogo import config as config_mod
        from pixellogo import jsonc
        from pixellogo.layout import build_scene
        from pixellogo.render import save
    except ImportError:
        # 渲染链路依赖 Pillow；纯查询命令（--version / --help / --list）不受影响
        print(f"{PROG}: {i18n.t('error.pillow')}", file=sys.stderr)
        return 2

    try:
        file_data = jsonc.load(args.config) if args.config else None
        cli_data = config_mod.cli_to_config(args)
        for item in args.set or []:
            key, sep, value = item.partition("=")
            if not sep or not key.strip():
                raise config_mod.ConfigError(
                    i18n.t("config.set.missing_key") + f" ({item!r})"
                )
            config_mod.set_path(cli_data, key.strip(), config_mod.coerce(value))
        settings_list = config_mod.resolve_many(file_data, cli_data, forced_out=args.out)
    except (ValueError, OSError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        print(i18n.t("cli.hint.help", prog=PROG), file=sys.stderr)
        return 2

    for settings in settings_list:
        for warning in settings.warnings:
            print(i18n.t("cli.warning", prog=PROG, message=warning), file=sys.stderr)

    if args.dry_run:
        payload = (settings_list[0].describe() if len(settings_list) == 1
                   else [item.describe() for item in settings_list])
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    used: set[Path] = set()
    results: list[dict] = []
    try:
        for settings in settings_list:
            diagnostics: list[str] = []
            scene = build_scene(settings.design, diagnostics)
            for message in diagnostics:
                print(i18n.t("cli.warning", prog=PROG, message=message), file=sys.stderr)
            targets = _unique(_targets(settings.out, settings.design.title,
                                       settings.mode_key, settings.formats), used)
            for target in targets:
                save(scene, target, scale=settings.scale)
            results.append({
                "files": [str(target) for target in targets],
                "mode": settings.mode_key,
                "width": scene.width * settings.scale,
                "height": scene.height * settings.scale,
                "format": settings.formats,
            })
    except (ValueError, OSError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 2

    if args.open and results and results[0]["files"]:
        webbrowser.open(Path(results[0]["files"][0]).resolve().as_uri())

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            for file in item["files"]:
                print(f"{file}  ({item['width']}×{item['height']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
