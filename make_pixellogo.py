"""
像素风格 Logo 生成器
风格参照：像素艺术 Logo（8-bit terminal aesthetic）
  - 硬边点阵字形，无抗锯齿、无渐变
  - 纯色块 + 右下偏移硬投影（无羽化）
  - 极简色板：浅冷灰底 / 高饱和主色 / 近黑字 / 单一暖色强调
  - 装饰：底部强调色横线 + 末端方块
"""
import os, subprocess, shutil
from PIL import Image, ImageFont, ImageDraw

# 所有路径相对于本脚本所在目录，保证整个文件夹可整体搬移
BASE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(BASE, "samples")
FONTS = os.path.join(BASE, "fonts")
os.makedirs(OUT, exist_ok=True)
os.makedirs(FONTS, exist_ok=True)

# 像素字体（随包自带，缺失时从 Google Fonts 兜底下载）
FONT_NAMES = {
    "PressStart2P": "https://fonts.gstatic.com/s/pressstart2p/v16/e3t4euO8T-267oIAQAu6jDQyK0nS.ttf",
    "Silkscreen":   "https://fonts.gstatic.com/s/silkscreen/v6/m8JXjfVPf62XiF7kO-i9ULQ.ttf",
    "PixelifySans":"https://fonts.gstatic.com/s/pixelifysans/v3/CHy2V-3HFUT7aC4iv1TxGDR9DHEserHN25py2TTp0H1Y.ttf",
}
for name, url in FONT_NAMES.items():
    dst = os.path.join(FONTS, name + ".ttf")
    if not os.path.exists(dst):
        try:
            import urllib.request
            urllib.request.urlretrieve(url, dst)
            print(f"  已下载字体 {name}.ttf")
        except Exception as e:
            print(f"  字体缺失且下载失败: {name} ({e})")

# ---------- 风格参数（实测自参考图） ----------
BG     = "#EEF1F6"   # 浅冷灰底
BLUE   = "#02ADFB"   # 高饱和主蓝
INK    = "#1F1F1F"   # 近黑字
ORANGE = "#FF6104"   # 唯一暖色强调
SHADOW = "#2B3444"   # 硬投影（深蓝黑）
ACCENT = "#FF6104"

W, H = 1080, 600


def alpha_mask(text, font_path, size):
    """渲染文本，返回 alpha 掩膜（仅轮廓，不含颜色）。"""
    font = ImageFont.truetype(font_path, size)
    tmp = Image.new("L", (6000, 3000), 0)
    ImageDraw.Draw(tmp).text((200, 200), text, font=font, fill=255)
    bbox = tmp.getbbox()
    return tmp.crop(bbox) if bbox else None


def rects_from_mask(mask, x, y, fill):
    """掩膜 -> 水平合并的 <rect> 列表字符串（真正的像素块，坐标全整数）。"""
    w, h = mask.size
    mp = mask.load()
    out = []
    for yy in range(h):
        run = []
        for xx in range(w):
            if mp[xx, yy] > 128:
                run.append(xx)
            elif run:
                out.append((run[0], yy, run[-1] - run[0] + 1, 1)); run = []
        if run:
            out.append((run[0], yy, run[-1] - run[0] + 1, 1))
    return "".join(
        f'<rect x="{x+rx}" y="{y+ry}" width="{rw}" height="{rh}" fill="{fill}"/>'
        for rx, ry, rw, rh in out
    )


def build(title, sub_lines, foot_lines, name, title_size=190, sub_size=46, foot_size=34,
          shadow_off=12):
    ps2  = os.path.join(FONTS, "PressStart2P.ttf")
    silk = os.path.join(FONTS, "Silkscreen.ttf")
    ps   = os.path.join(FONTS, "PixelifySans.ttf")

    tm   = alpha_mask(title, ps2, title_size)
    subs = [alpha_mask(t, silk, sub_size) for t in sub_lines]
    foots= [alpha_mask(t, ps,   foot_size) for t in foot_lines]

    L = 64
    p = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    # --- 主标题：投影层（右下偏移）→ 主体层 ---
    ty = 70
    p.append(rects_from_mask(tm, L + shadow_off, ty + shadow_off, SHADOW))
    p.append(rects_from_mask(tm, L, ty, BLUE))

    # --- 副标题 ---
    y = ty + tm.size[1] + 44
    for m in subs:
        p.append(rects_from_mask(m, L, y, INK))
        y += m.size[1] + 26

    # --- 强调横线 + 末端方块 ---
    y += 34
    line_w = 430
    p.append(f'<rect x="{L}" y="{y}" width="{line_w}" height="8" fill="{ORANGE}"/>')
    p.append(f'<rect x="{L+line_w-18}" y="{y-7}" width="24" height="22" fill="{ORANGE}"/>')

    # --- 底部说明文字 ---
    y += 52
    for m in foots:
        p.append(rects_from_mask(m, L, y, INK))
        y += m.size[1] + 26

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" shape-rendering="crispEdges">' + "".join(p) + "</svg>")
    sp = os.path.join(OUT, name + ".svg")
    open(sp, "w", encoding="utf-8").write(svg)

    # --- SVG -> PNG（Chrome headless，2x）---
    png = os.path.join(OUT, name + ".png")
    if os.path.exists(png):
        os.remove(png)
    chrome = None
    for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]:
        if os.path.exists(c):
            chrome = c
            break
    if not chrome:
        print(f"  {name}: 未找到 Chrome/Edge，无法转 PNG")
        return sp, png
    cmd = [chrome,
           "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=2", f"--screenshot={png}",
           "--window-size=1080,600", "file:///" + sp.replace("\\", "/")]
    subprocess.run(cmd, capture_output=True, timeout=120)
    print(f"  {name}: SVG={sp}  PNG={'OK ' + str(Image.open(png).size) if os.path.exists(png) else 'FAIL'}")
    return sp, png


# ================= 内容区（跟风格无关，改这里） =================
# 每条内容 = 一个成品：标题 / 副标题若干行 / 底部说明若干行 / 输出文件名
CONTENT = [
    {
        "title": "REA",
        "sub":   ["REVERSE ENGINEER", "ANYTHING"],
        "foot":  ["One CLI + MCP server for agents", "From binaries to websites"],
        "name":  "rea_pixel",
    },
    {
        "title": "DEV",
        "sub":   ["BUILD FASTER", "SHIP SMARTER"],
        "foot":  ["Agent-native tooling for modern teams",
                  "From prototype to production in days"],
        "name":  "dev_pixel",
    },
]

print("=== 生成 ===")
for c in CONTENT:
    build(c["title"], c["sub"], c["foot"], c["name"])
