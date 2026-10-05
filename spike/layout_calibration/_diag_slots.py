"""按槽/按区域诊断我们 vs .NET 参考的剩余差异（开发用）。"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import helpers  # noqa: E402
from koutu.core import layout  # noqa: E402

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Administrator\AppData\Local\Temp\koutu_probe")

net = helpers.load_rgba(TEMP / "fullpage_net.png")
ours = helpers.load_rgba(TEMP / "ours_w2" / "第1页.png")
d = np.abs(ours[..., :3].astype(np.int16) - net[..., :3].astype(np.int16)).max(axis=2)
mask = d > 8
ys, xs = np.nonzero(mask)
print(f"总差异 {mask.sum()} ({mask.sum()/(2480*3508):.4%})")
vals = d[mask]
print("|Δ| 分布:", {f">{t}": int((vals > t).sum()) for t in (8, 16, 32, 64, 128)})

slots = layout.detect_slots(layout.imaging.load_rgb(REPO / "排版demo.png"))
px = xs + 0.5
py = ys + 0.5
best = np.full(len(xs), -1, dtype=int)
mind = np.full(len(xs), 1e18)
for k, s in enumerate(slots):
    dd = np.sqrt((px - s.cx) ** 2 + (py - s.cy) ** 2)
    upd = dd < mind
    mind[upd] = dd[upd]
    best[upd] = k

print("\n按槽（最近槽归属）:")
for k in range(len(slots)):
    sel = best == k
    if sel.sum() == 0:
        continue
    near = mind[sel]
    print(
        f"  槽{k+1}: 共{int(sel.sum()):>6}  内{int((near <= slots[k].r - 12).sum()):>6}"
        f"  边缘带{int(((near > slots[k].r - 12) & (near < slots[k].r + 12)).sum()):>6}"
        f"  角区{int((near >= slots[k].r + 12).sum()):>6}"
    )

# 每槽差异的 bbox 与样本
print("\n每槽 bbox 示例:")
for k in range(len(slots)):
    sel = best == k
    if sel.sum() == 0:
        continue
    xk, yk = xs[sel], ys[sel]
    print(f"  槽{k+1}: x {xk.min()}..{xk.max()}  y {yk.min()}..{yk.max()}")
    for j in range(min(3, sel.sum())):
        x, y = int(xk[j]), int(yk[j])
        print(f"    ({x},{y}) ours={ours[y, x, :3].tolist()} net={net[y, x, :3].tolist()} Δ={int(d[y, x])}")

# 检查一个特例：槽7 的角区（其 bbox 是否在源图边缘）
info7 = None
infos, _ = layout.load_base_infos(REPO / "golden" / "baseline_products" / "底图")
print("\n底图列表:", [(i.name, i.min_x, i.min_y, i.max_x, i.max_y) for i in infos])
