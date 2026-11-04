"""把 docs/gallery.md 编译成画廊页面用的数据文件。

维护者只改 Markdown：新增一个 ``###`` 小节、放一张图、贴一条命令，
再运行本脚本，``docs/gallery-data.js`` 就会重新生成，页面无需手工编辑。

约定（与 docs/gallery.md 现有写法一致）::

    ## 分类标题（可选附注）        -> 一个筛选分组
    > English section label        -> 该分组的英文名

    ### 标题 · 中文说明            -> 一张图；标题取自命令里的 -t，这里只提供说明
    > English note                 -> 该图的英文说明
    <img src="images/gallery/x.png" width="480" alt="...">
    ```bash
    pixellogo ... -m poster -o docs/images/gallery/x.png
    ```

命令是唯一事实来源：画布、预设、纹理、标题都从命令里解析，图片路径取自 ``-o``。
缺少英文说明时回退到中文，页面不会出现空白。

用法::

    python tools/gallery_site.py              # 生成 docs/gallery-data.js
    python tools/gallery_site.py --check      # 只校验，不写文件（CI 用）

``--check`` 会检查三件事：图片文件是否存在、命令的 ``-o`` 是否指向该图、
每张图是否都有可运行的命令。任何一条不满足都以退出码 1 结束。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "gallery.md")
DOCS_DIR = os.path.join(ROOT, "docs")
OUT_JS = os.path.join(DOCS_DIR, "gallery-data.js")

#: 画布 -> (英文名, 宽, 高)。与 src/pixellogo/modes.py 保持一致。
MODES = {
    "poster": ("poster", 1080, 1440),
    "card": ("card", 1440, 1080),
    "banner": ("banner", 1280, 640),
    "slide": ("slide", 1920, 1080),
    "square": ("square", 1080, 1080),
}

ALIASES = {
    "xhs": "poster", "xiaohongshu": "poster", "red": "poster", "redbook": "poster",
    "3:4": "poster", "3x4": "poster", "portrait": "poster", "story": "poster",
    "4:3": "card", "4x3": "card", "landscape": "card",
    "og": "banner", "github": "banner", "repo": "banner", "social": "banner",
    "open-graph": "banner", "2:1": "banner", "2x1": "banner",
    "16:9": "slide", "16x9": "slide", "wide": "slide", "widescreen": "slide",
    "1:1": "square", "1x1": "square", "avatar": "square",
}

#: 取最后一个值的参数（同名字段重复时后者覆盖前者，与命令行一致）
VALUE_FLAGS = {
    "-t": "title", "--title": "title",
    "-m": "mode", "--mode": "mode",
    "-p": "preset", "--preset": "preset",
    "-o": "out", "--out": "out",
    "--size": "size",
    "--bg-pattern": "pattern",
    "--divider": "divider",
    "--badge": "badge",
    "--eyebrow": "eyebrow",
    "-f": "format", "--format": "format",
}
#: 可重复参数
LIST_FLAGS = {"-s": "subtitle", "--subtitle": "subtitle", "-d": "desc", "--desc": "desc"}

TIMELINE_HEADING = re.compile(r"更新记录|changelog", re.I)


def slugify(text: str) -> str:
    """英文分组名 -> 稳定的锚点 key。"""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def strip_note(heading: str) -> str:
    """去掉标题里的画布附注，例如「竖版海报（``poster``，1080×1440）」-> 「竖版海报」。"""
    return re.sub(r"[（(].*?[)）]", "", heading).strip()


def split_heading(heading: str) -> tuple[str, str]:
    """「慢生活 · 糖果粉 + 点阵」-> ("慢生活", "糖果粉 + 点阵")。"""
    if " · " in heading:
        title, note = heading.split(" · ", 1)
        return title.strip(), note.strip()
    return heading.strip(), ""


def parse_command(command: str) -> dict:
    """解析一条 pixellogo 命令，取出画布/预设/纹理/标题等。"""
    info: dict = {"subtitle": [], "desc": []}
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        key = VALUE_FLAGS.get(token)
        if key and index + 1 < len(tokens):
            info[key] = tokens[index + 1]
            index += 2
            continue
        list_key = LIST_FLAGS.get(token)
        if list_key and index + 1 < len(tokens):
            info[list_key].append(tokens[index + 1])
            index += 2
            continue
        index += 1

    mode_key = (info.get("mode") or "poster").strip().lower()
    mode_key = ALIASES.get(mode_key, mode_key)
    info["canvas"], width, height = MODES.get(mode_key, MODES["poster"])

    size = info.get("size")
    if size and "x" in size.lower():
        try:
            w, h = size.lower().split("x", 1)
            width, height = int(w), int(h)
            info["canvas"] = "custom"
        except ValueError:
            pass

    info["width"], info["height"] = width, height
    info["pattern"] = info.get("pattern") or "none"
    return info


def parse_markdown(text: str) -> dict:
    lines = text.splitlines()
    sections: list[dict] = []
    timeline: list[dict] = []

    section: dict | None = None
    item: dict | None = None
    pending_section_en: str | None = None
    in_code = False
    code_lines: list[str] = []

    def close_item() -> None:
        nonlocal item
        if item is None:
            return
        if item.get("command") and item.get("image"):
            if section is not None:
                section["items"].append(item)
        item = None

    def close_section() -> None:
        nonlocal section
        close_item()
        if section is not None and (section["items"] or section.get("timeline")):
            section["key"] = slugify(section["en"] or section["zh"])
            sections.append(section)
        section = None

    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                in_code = False
                if item is not None and code_lines:
                    # 文档里的命令用行尾反斜杠折行，拼回一行时要去掉它
                    parts = [part.strip().rstrip("\\").strip() for part in code_lines]
                    command = " ".join(part for part in parts if part)
                    if command.startswith("pixellogo"):
                        item["command"] = command
                code_lines = []
            else:
                in_code = True
                code_lines = []
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if stripped.startswith("## "):
            close_section()
            heading = stripped[3:].strip()
            if TIMELINE_HEADING.search(heading):
                section = {"zh": strip_note(heading), "en": "Changelog",
                           "items": [], "timeline": timeline}
            else:
                section = {"zh": strip_note(heading), "en": "", "items": []}
            pending_section_en = None
            index += 1
            continue

        if stripped.startswith("### "):
            close_item()
            heading = stripped[4:].strip()
            title_zh, note_zh = split_heading(heading)
            item = {"titleZh": title_zh, "noteZh": note_zh, "noteEn": "",
                    "image": "", "command": ""}
            index += 1
            continue

        if section is not None and stripped.startswith("> "):
            quote = stripped[2:].strip()
            if item is not None and not item["image"]:
                if not item["noteEn"]:
                    item["noteEn"] = quote
            elif not section["items"] and not section.get("timeline") and not section["en"]:
                pending_section_en = quote
                section["en"] = quote
            index += 1
            continue

        img = re.search(r'<img[^>]*src="([^"]+)"', stripped)
        if img and item is not None and not item["image"]:
            item["image"] = img.group(1)
            index += 1
            continue

        if section is not None and section.get("timeline") is not None:
            entry = re.match(r"^-\s+(\d{4}-\d{2}-\d{2})\s*\|\s*(.+)$", stripped)
            if entry:
                parts = [part.strip() for part in entry.group(2).split("|")]
                timeline.append({
                    "date": entry.group(1),
                    "zh": parts[0] if parts else "",
                    "en": parts[1] if len(parts) > 1 else parts[0],
                })
                index += 1
                continue

        index += 1

    close_section()

    # 更新记录不是图片分组，单独留在 timeline 里
    sections = [sec for sec in sections if sec["items"]]

    # 命令里的 -t 才是图上真正印着的标题，Markdown 标题只提供说明
    for sec in sections:
        for entry in sec["items"]:
            parsed = parse_command(entry["command"])
            entry["title"] = parsed.get("title") or entry["titleZh"]
            entry["canvas"] = parsed["canvas"]
            entry["width"] = parsed["width"]
            entry["height"] = parsed["height"]
            entry["preset"] = parsed.get("preset", "")
            entry["pattern"] = parsed["pattern"]
            entry["divider"] = parsed.get("divider", "")
            entry["badge"] = parsed.get("badge", "")
            entry["out"] = parsed.get("out", "")
            entry["noteEn"] = entry["noteEn"] or entry["noteZh"]
            entry["hasTitle"] = bool(parsed.get("title"))
            del parsed

    return {"sections": sections, "timeline": timeline}


def validate(data: dict) -> list[str]:
    """检查图片、命令、输出路径三者是否自洽。"""
    problems: list[str] = []
    for sec in data["sections"]:
        for entry in sec["items"]:
            image_path = os.path.join(DOCS_DIR, entry["image"])
            if not os.path.isfile(image_path):
                problems.append("图片不存在: %s" % entry["image"])
            out = entry.get("out", "")
            if not out:
                problems.append("命令缺少 -o: %s" % entry["image"])
            elif os.path.basename(out.replace("\\", "/")) != os.path.basename(entry["image"]):
                problems.append("命令的 -o 与图片不一致: %s != %s"
                                % (os.path.basename(out), os.path.basename(entry["image"])))
            if not entry.get("hasTitle"):
                problems.append("命令缺少标题: %s" % entry["image"])
    if not data["sections"]:
        problems.append("没有解析到任何图片，检查 docs/gallery.md 的结构")
    return problems


def build_js(data: dict) -> str:
    tz = timezone(timedelta(hours=8))
    payload = {
        "generated": datetime.now(tz).strftime("%Y-%m-%d %H:%M"),
        "sections": data["sections"],
        "timeline": data["timeline"],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return ("/* 由 tools/gallery_site.py 从 docs/gallery.md 生成，请勿手工编辑。 */\n"
            "window.GALLERY_DATA = " + body + ";\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 docs/gallery.md 生成画廊数据")
    parser.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = parser.parse_args(argv)

    with open(DOC, encoding="utf-8") as handle:
        text = handle.read()

    data = parse_markdown(text)
    problems = validate(data)

    total = sum(len(sec["items"]) for sec in data["sections"])
    print("解析到 %d 个分组、%d 张图、%d 条更新记录"
          % (len(data["sections"]), total, len(data["timeline"])))
    for sec in data["sections"]:
        print("  %-24s %-28s %2d" % (sec["key"], sec["en"], len(sec["items"])))

    if problems:
        for problem in problems:
            print("✗ " + problem, file=sys.stderr)
        return 1

    if args.check:
        print("✓ 校验通过")
        return 0

    with open(OUT_JS, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_js(data))
    print("✓ 写入 %s" % os.path.relpath(OUT_JS, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
