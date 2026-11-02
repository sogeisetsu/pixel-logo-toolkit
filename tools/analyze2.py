from PIL import Image
from collections import Counter
import os, sys, json

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "reference_style.png")
im = Image.open(SRC).convert("RGB")
W, H = im.size
px = im.load()

BLUE = (2, 173, 251)

def is_blue(p, t=60):
    return abs(p[0]-BLUE[0])<t and abs(p[1]-BLUE[1])<t and abs(p[2]-BLUE[2])<t

def is_dark(p, t=60):
    return p[0]<90 and p[1]<90 and p[2]<90

# 找 REA 的蓝色区域（排除右面板）
xs = [(x,y) for y in range(H) for x in range(0, W//2) if is_blue(px[x,y])]
x0 = min(p[0] for p in xs); x1 = max(p[0] for p in xs)
y0 = min(p[1] for p in xs); y1 = max(p[1] for p in xs)
print(f"REA blue bbox: ({x0},{y0})-({x1},{y1})  w={x1-x0+1} h={y1-y0+1}")

# 垂直/水平连续蓝段的直方图 -> 网格单位
vr = []
for x in range(x0, x1+1):
    colv = [y for y in range(y0, y1+1) if is_blue(px[x,y])]
    if not colv: continue
    seg = 1
    for i in range(1, len(colv)):
        if colv[i] == colv[i-1]+1: seg += 1
        else: vr.append(seg); seg = 1
    vr.append(seg)
hr = []
for y in range(y0, y1+1):
    row = [x for x in range(x0, x1+1) if is_blue(px[x,y])]
    if not row: continue
    seg = 1
    for i in range(1, len(row)):
        if row[i] == row[i-1]+1: seg += 1
        else: hr.append(seg); seg = 1
    hr.append(seg)
print("vertical blue run lens:", sorted(Counter(vr).items()))
print("horizontal blue run lens:", sorted(Counter(hr).items()))

# 分离三个字母：按 x 的空白间隔
colhas = [any(is_blue(px[x,y]) for y in range(y0,y1+1)) for x in range(x0,x1+1)]
letters = []; s=None
for i,v in enumerate(colhas):
    if v and s is None: s=i
    if not v and s is not None:
        letters.append((x0+s, x0+i-1)); s=None
if s is not None: letters.append((x0+s, x1))
print("letters:", [(a, b, b-a+1) for a,b in letters])

for i,(a,b) in enumerate(letters):
    print(f"  letter#{i} x[{a},{b}] w={b-a+1}")

# 投影：找 R 字母右下方深色偏移
la, lb = letters[0]
print("\n--- shadow probe (letter R region) ---")
for dx in range(0, 22):
    cnt = 0
    for yy in range(y0, y1+1):
        for xx in range(la, lb+1):
            if is_blue(px[xx,yy]) and is_dark(px[min(W-1,xx+dx), min(H-1,yy+dx)]):
                cnt += 1
    if cnt > 0:
        print(f"  offset(+{dx},{dx}) dark-behind-blue pixels = {cnt}")

# 描边检测：蓝像素正上方/左方是否为深色
print("\n--- outline probe ---")
up=lef=0; tot=0
for yy in range(y0, y1+1):
    for xx in range(x0, x1+1):
        if is_blue(px[xx,yy]):
            tot+=1
            if is_dark(px[xx, yy-1]) if yy-1>=0 else False: up+=1
            if is_dark(px[xx-1, yy]) if xx-1>=0 else False: lef+=1
print(f"  blue px={tot}  with dark ABOVE={up}  with dark LEFT={lef}")

# 橙色分隔线
print("\n--- orange rule ---")
oxs = [(x,y) for y in range(H) for x in range(W//2) if px[x,y][0]>200 and 90<px[x,y][1]<180 and px[x,y][2]<90]
if oxs:
    ox0=min(p[0] for p in oxs); ox1=max(p[0] for p in oxs)
    oy0=min(p[1] for p in oxs); oy1=max(p[1] for p in oxs)
    print(f"  bbox ({ox0},{oy0})-({ox1},{oy1})  len={ox1-ox0+1} thickness={oy1-oy0+1}")
    print(f"  color sample mid: #{px[(ox0+ox1)//2, (oy0+oy1)//2][0]:02X}{px[(ox0+ox1)//2,(oy0+oy1)//2][1]:02X}{px[(ox0+ox1)//2,(oy0+oy1)//2][2]:02X}")
    # 末端方块
    for x in range(ox1-14, ox1+1):
        ys = [y for y in range(oy0, oy1+16) if px[x,y][0]>200 and 90<px[x,y][1]<180 and px[x,y][2]<90]
        if ys: print(f"    x={x} orange rows {min(ys)}..{max(ys)} h={max(ys)-min(ys)+1}")

# 副标题文本行（暗色）
print("\n--- subtitle text rows (left panel, dark) ---")
rows = []
for y in range(H):
    n = sum(1 for x in range(0, W//2) if is_dark(px[x,y]))
    rows.append(n)
band=None
for y,n in enumerate(rows):
    if n>2 and band is None: band=y
    if n<=2 and band is not None:
        print(f"  band {band}..{y-1} h={y-band}"); band=None
if band is not None: print(f"  band {band}..{H-1}")

# 副标题笔画宽度：取一行做水平run
print("\n--- subtitle stroke width probe ---")
for probe_y in [290, 300, 330, 425, 445]:
    rr=[]; s=None
    for x in range(0, W//2):
        d = is_dark(px[x,probe_y])
        if d and s is None: s=x
        if not d and s is not None: rr.append(x-s); s=None
    if s is not None: rr.append(W//2-s)
    print(f"  y={probe_y} dark run lens: {sorted(Counter(rr).items())}")

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis")
os.makedirs(OUT, exist_ok=True)
json.dump({"W":W,"H":H}, open(os.path.join(OUT, "meta.json"), "w"))
