"""排版合成细扫（开发用，不参与 pytest 收集）。

在单槽区域上扫描：亚像素相位（δx, δy）→ 卷积参数 a → 差异分布。
目标：找出与 GDI+ `DrawImage` 对齐最接近的组合。
"""

import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from koutu.core import imaging, layout  # noqa: E402


def make_patch(slot, info, dx_shift, dy_shift, a, premult=False):
    dest_x = slot.cx - slot.r - 1.0
    dest_y = slot.cy - slot.r - 1.0
    dest_w = dest_h = 2.0 * slot.r + 2.0
    src_x = float(info.min_x - 1)
    src_y = float(info.min_y - 1)
    src_w = float(info.max_x - info.min_x + 3)
    src_h = float(info.max_y - info.min_y + 3)
    rx0 = int(math.floor(dest_x)) - 1
    ry0 = int(math.floor(dest_y)) - 1
    rx1 = int(math.ceil(dest_x + dest_w)) + 2
    ry1 = int(math.ceil(dest_y + dest_h)) + 2
    xs = np.arange(rx0, rx1, dtype=np.float64) + 0.5
    ys = np.arange(ry0, ry1, dtype=np.float64) + 0.5
    sx = src_x + (xs - dest_x) * (src_w / dest_w) - 0.5 + dx_shift
    sy = src_y + (ys - dest_y) * (src_h / dest_h) - 0.5 + dy_shift
    img = info.image.astype(np.float64)
    if premult:
        img = img.copy()
        img[..., :3] *= img[..., 3:4] / 255.0
    s = layout._sample_2d(img, sx, sy, a)
    alpha = s[..., 3]
    if premult:
        out = s[..., :3] + (255.0 - alpha)[..., None]
    else:
        out = s[..., :3] * (alpha / 255.0)[..., None] + (255.0 - alpha)[..., None]
    out = np.clip(np.floor(out + 0.5), 0.0, 255.0)
    return out.astype(np.uint8), (rx0, ry0)


def score(page, patch, px0, py0):
    ph, pw = patch.shape[0], patch.shape[1]
    g = page[py0 : py0 + ph, px0 : px0 + pw, :3]
    d = np.abs(patch.astype(np.int16) - g.astype(np.int16))
    return int((d.max(axis=2) > 8).sum()), float(d.mean()), int(d.max()), d


def main() -> None:
    demo = REPO / "排版demo.png"
    golden_root = REPO / "golden" / "baseline_products"
    page = imaging.load_rgba(golden_root / "已排版" / "第1页.png")
    template = imaging.load_rgb(demo)
    slots = layout.detect_slots(template)
    infos, _ = layout.load_base_infos(golden_root / "底图")
    slot, info = slots[0], infos[0]
    print("info bbox:", info.min_x, info.min_y, info.max_x, info.max_y)
    print("slot:", slot)

    total = None

    def run(dxs, dys, a, premult=False, tag=""):
        nonlocal total
        best = None
        for dx in dxs:
            for dy in dys:
                patch, (px0, py0) = make_patch(slot, info, dx, dy, a, premult)
                total = patch.shape[0] * patch.shape[1]
                gt8, mean, mx, d = score(page, patch, px0, py0)
                row = (gt8, mean, mx, dx, dy)
                if best is None or row[:2] < best[:2]:
                    best = row
                print(f"[{tag}] a={a} premult={premult} dx={dx:+.3f} dy={dy:+.3f}  "
                      f"gt8={gt8:>7} ({gt8/total:.3%})  mean={mean:.4f}  max={mx}")
        return best

    print("== 粗扫：相位（a=-0.5） ==")
    best = run([-0.5, -0.25, 0.0, 0.25, 0.5], [-0.5, -0.25, 0.0, 0.25, 0.5], -0.5, tag="coarse")
    bgt8, bmean, bmx, bdx, bdy = best
    print("粗扫最优:", best.__str__() if False else (bgt8, bmean, bdx, bdy))

    print("== 细扫：最优相位 ±0.125 ==")
    fx = [bdx + v for v in (-0.125, -0.0625, 0.0, 0.0625, 0.125)]
    fy = [bdy + v for v in (-0.125, -0.0625, 0.0, 0.0625, 0.125)]
    best2 = run(fx, fy, -0.5, tag="fine")
    b2gt8, b2mean, b2mx, b2dx, b2dy = best2
    print("细扫最优:", (b2gt8, b2mean, b2dx, b2dy))

    print("== 核参数扫描（在细扫最优相位上） ==")
    for a in (-1.0, -0.75, -0.5, -0.25, 0.0):
        for premult in (False, True):
            patch, (px0, py0) = make_patch(slot, info, b2dx, b2dy, a, premult)
            gt8, mean, mx, d = score(page, patch, px0, py0)
            print(f"[kernel] a={a} premult={premult}  gt8={gt8:>7} ({gt8/total:.3%})  mean={mean:.4f}  max={mx}")

    print("== 最优组合下的差异分布 ==")
    patch, (px0, py0) = make_patch(slot, info, b2dx, b2dy, -0.5)
    ph, pw = patch.shape[0], patch.shape[1]
    yy, xx = np.mgrid[0:ph, 0:pw]
    ccx = slot.cx - px0
    ccy = slot.cy - py0
    rr = slot.r
    dd = np.sqrt((xx + 0.5 - ccx) ** 2 + (yy + 0.5 - ccy) ** 2)
    g = page[py0 : py0 + ph, px0 : px0 + pw, :3]
    dmask = (np.abs(patch.astype(np.int16) - g.astype(np.int16)).max(axis=2) > 8)
    inner = dmask[dd <= rr - 20].sum()
    ring = dmask[(dd > rr - 20) & (dd <= rr + 10)].sum()
    outer = dmask[dd > rr + 10].sum()
    print(f"inner(兜径-20 内)={inner}  ring(±20/10)={ring}  outer={outer}  total={dmask.sum()}")


if __name__ == "__main__":
    main()
