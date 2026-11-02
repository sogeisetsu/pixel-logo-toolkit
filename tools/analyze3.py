import os, sys
from PIL import Image
from math import gcd
from functools import reduce
from collections import Counter

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "reference_style.png")
im = Image.open(SRC).convert("RGB")
W, H = im.size
px = im.load()

def is_blue(p, t=60):
    return abs(p[0]-2)<t and abs(p[1]-173)<t and abs(p[2]-251)<t
def is_dark(p):
    return p[0]<100 and p[1]<100 and p[2]<100

# ---- REA 完整范围 (不限 W//2) ----
blue = [(x,y) for y in range(H) for x in range(W) if is_blue(px[x,y])]
bx0=min(p[0] for p in blue); bx1=max(p[0] for p in blue)
by0=min(p[1] for p in blue); by1=max(p[1] for p in blue)
print(f"REA full bbox ({bx0},{by0})-({bx1},{by1}) w={bx1-bx0+1} h={by1-by0+1}")

vr=[];hr=[]
for x in range(bx0,bx1+1):
    col=[y for y in range(by0,by1+1) if is_blue(px[x,y])]
    if not col: continue
    s=1
    for i in range(1,len(col)):
        if col[i]==col[i-1]+1: s+=1
        else: vr.append(s); s=1
    vr.append(s)
for y in range(by0,by1+1):
    row=[x for x in range(bx0,bx1+1) if is_blue(px[x,y])]
    if not row: continue
    s=1
    for i in range(1,len(row)):
        if row[i]==row[i-1]+1: s+=1
        else: hr.append(s); s=1
    hr.append(s)
print("GCD of vertical runs  :", reduce(gcd, vr))
print("GCD of horizontal runs:", reduce(gcd, hr))
print("common run lens (v):", sorted(Counter(vr).items())[:10])
print("common run lens (h):", sorted(Counter(hr).items())[:10])

# ---- ASCII 地图：字母 A 区域 ----
def ascii_map(x0,y0,x1,y1,step=2):
    for y in range(y0,y1,step):
        line=""
        for x in range(x0,x1,step):
            p=px[x,y]
            line += "#" if is_blue(p) else ("+" if is_dark(p) else ".")
        print("   "+line)

print("\n=== 字母 A (step=3) ===")
ascii_map(370,115,475,250,3)
print("\n=== 字母 R (step=3) ===")
ascii_map(50,115,180,250,3)

# ---- 小字号文本网格 (GCD) ----
def band_grid(y0,y1,label):
    rv=[];rh=[]
    for x in range(40,540):
        col=[y for y in range(y0,y1) if is_dark(px[x,y])]
        if not col: continue
        s=1
        for i in range(1,len(col)):
            if col[i]==col[i-1]+1: s+=1
            else: rv.append(s); s=1
        rv.append(s)
    for y in range(y0,y1):
        row=[x for x in range(40,540) if is_dark(px[x,y])]
        if not row: continue
        s=1
        for i in range(1,len(row)):
            if row[i]==row[i-1]+1: s+=1
            else: rh.append(s); s=1
        rh.append(s)
    print(f"{label} y[{y0},{y1}] GCD v={reduce(gcd,rv)} h={reduce(gcd,rh)}  runs h={sorted(Counter(rh).items())[:8]}")

band_grid(284,313,"subtitle line1")
band_grid(336,364,"subtitle line2")
band_grid(428,443,"bottom line1")
band_grid(467,484,"bottom line2")
