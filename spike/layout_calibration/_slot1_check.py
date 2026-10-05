"""单槽深度对照（开发用）：当前核 vs .NET 单槽渲染；>128 差异的角向分布。"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import helpers  # noqa: E402
from koutu.core import layout  # noqa: E402

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Administrator\AppData\Local\Temp\koutu_probe")

probe = helpers.load_rgba(TEMP / "probe_slot1.png")
template = layout.imaging.load_rgb(REPO / "排版demo.png")
slots = layout.detect_slots(template)
infos, _ = layout.load_base_infos(REPO / "golden" / "baseline_products" / "底图")
slot, info = slots[0], infos[0]


def check(a_value, tag):
    patch, (px0, py0) = layout._render_slot_patch(slot, info, a=a_value)
    ph, pw = patch.shape[0], patch.shape[1]
    g = probe[py0 : py0 + ph, px0 : px0 + pw, :3]
    d = np.abs(patch.astype(np.int16) - g.astype(np.int16)).max(axis=2)
    mask = d > 8
    big = d > 128
    print(f"[{tag}] gt8={int(mask.sum())} ({mask.mean():.4%})  >128: {int(big.sum())}")
    if big.sum():
        ys, xs = np.nonzero(big)
        # 相对槽心的角度 & 半径
        ccx = slot.cx - px0
        ccy = slot.cy - py0
        ang = np.degrees(np.arctan2(ys + 0.5 - ccy, xs + 0.5 - ccx)) % 360
        rad = np.sqrt((xs + 0.5 - ccx) ** 2 + (ys + 0.5 - ccy) ** 2)
        sectors = np.histogram(ang, bins=8, range=(0, 360))[0]
        print("  >128 八扇区计数(0°=右,顺时针90°=下):", sectors.tolist())
        print(f"  >128 半径范围: {rad.min():.0f}..{rad.max():.0f}（槽半径 {slot.r:.0f}）")
        for j in range(min(4, big.sum())):
            x, y = int(xs[j]), int(ys[j])
            print(f"    ({px0+x},{py0+y}) ours={patch[y, x, :3].tolist()} net={g[y, x, :3].tolist()} Δ={int(d[y, x])}")


check(layout.COMPOSITE_A, "current-kernel")
check(-0.5, "keys(-0.5)")
