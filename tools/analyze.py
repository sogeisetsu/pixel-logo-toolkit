from PIL import Image
from collections import Counter
import os, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "reference_style.png")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "analysis")
os.makedirs(OUT, exist_ok=True)

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("SIZE:", W, H, "ratio", round(W/H, 4))

px = im.load()

# 1. 全局主色
c = Counter(px[x, y] for y in range(0, H, 2) for x in range(0, W, 2))
print("\n--- TOP COLORS ---")
for col, n in c.most_common(12):
    print(f"  #{col[0]:02X}{col[1]:02X}{col[2]:02X}  rgb{col}  {n}")

def bbox(pred):
    xs, ys = [], []
    for y in range(H):
        for x in range(W):
            if pred(px[x, y]):
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))

def near(col, t=30):
    return lambda p: abs(p[0]-col[0]) < t and abs(p[1]-col[1]) < t and abs(p[2]-col[2]) < t

print("\n--- REGION BBOX ---")
print("background corner:", px[2, 2], " -> #%02X%02X%02X" % px[2, 2])
print("orange:", bbox(near((245, 130, 32), 60)))
print("blue  :", bbox(near((41, 171, 226), 70)))

# 2. 蓝色 REA 的像素网格单位：统计横向上连续同色段的长度分布
print("\n--- REA 像素网格推断 ---")
bb = bbox(near((41, 171, 226), 70))
if bb:
    x0, y0, x1, y1 = bb
    runs = []
    for y in range(y0, y1 + 1):
        row = [x for x in range(x0, x1 + 1) if near(px[x, y], 70)(px[x, y])]
        if not row: continue
        seg = 1
        for i in range(1, len(row)):
            if row[i] == row[i-1] + 1: seg += 1
            else: runs.append(seg); seg = 1
        runs.append(seg)
    from collections import Counter as C2
    print("  horizontal run lengths:", sorted(C2(runs).items())[:12])
    vruns = []
    for x in range(x0, x1 + 1):
        colv = [y for y in range(y0, y1 + 1) if near(px[x, y], 70)(px[x, y])]
        if not colv: continue
        seg = 1
        for i in range(1, len(colv)):
            if colv[i] == colv[i-1] + 1: seg += 1
            else: vruns.append(seg); seg = 1
        vruns.append(seg)
    print("  vertical run lengths  :", sorted(C2(vruns).items())[:12])
    print("  REA bbox:", bb, "w", x1-x0+1, "h", y1-y0+1)

# 3. 深色文字行分布（按行统计暗像素）
print("\n--- 暗色文字行分布 ---")
dark_rows = []
for y in range(H):
    n = sum(1 for x in range(W) if sum(px[x, y]) < 330)
    dark_rows.append(n)
band = None
for y, n in enumerate(dark_rows):
    if n > 0 and band is None: band = y
    if n == 0 and band is not None:
        print(f"  dark band rows {band}..{y-1} (h={y-band})")
        band = None
if band is not None: print(f"  dark band rows {band}..{H-1}")

# 4. 裁切放大关键区域
def crop_zoom(name, box, scale):
    a, b, cc, d = box
    img = im.crop(box)
    img = img.resize((img.width*scale, img.height*scale), Image.NEAREST)
    p = os.path.join(OUT, name)
    img.save(p)
    print("SAVED", p, img.size)

if bb:
    crop_zoom("rea_zoom.png", (max(0, bb[0]-8), max(0, bb[1]-8), min(W, bb[2]+9), min(H, bb[3]+9)), 3)
crop_zoom("sub_zoom.png", (30, 250, 520, 350), 3)
crop_zoom("bottom_zoom.png", (30, 400, 520, 470), 3)
crop_zoom("line_zoom.png", (30, 355, 500, 395), 4)
