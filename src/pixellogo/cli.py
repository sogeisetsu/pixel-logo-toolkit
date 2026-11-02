"""命令行入口。"""
from __future__ import annotations

import argparse
import sys

from pixellogo import __version__

PROG = "pixellogo"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="生成 8-bit / 复古终端风格的像素图（PNG / SVG）。",
    )
    parser.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "handled", False):
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
