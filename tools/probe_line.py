import os, sys
from PIL import Image
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "reference_style.png")
im = Image.open(SRC).convert("RGB"); px = im.load()
def is_o(p): return p[0]>200 and 90<p[1]<190 and p[2]<110
print("=== 橙线末端像素剖面 (x 250..285) ===")
for x in range(250, 285):
    ys = [y for y in range(380, 410) if is_o(px[x,y])]
    print(f"  x={x}: rows {ys[0] if ys else '-'}..{ys[-1] if ys else '-'}  n={len(ys)}")
print("\n=== 参考图 REA 比例 ===")
print("  REA x 53..464 (w=412)  y 123..240 (h=118)")
print("  大字纵向笔画 ~15-16px, 横向 ~30px  => 像素格 ~15px")
print("  小字笔画 6px")
