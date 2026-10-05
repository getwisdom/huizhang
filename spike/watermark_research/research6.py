"""水印域测绘 v7（W3.1）：亚像素周期精定 + 相位优化折叠出字形。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def find_repo() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "koutu").is_dir() and (parent / "golden").is_dir():
            return parent
    raise RuntimeError("repo not found")


REPO = find_repo()
BASE = REPO / "golden" / "baseline_products" / "底图"


def load_luma(path: Path):
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    rgb = rgba[..., :3].astype(np.float32)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2], rgba[..., 3]


def med(L, size=21):
    u8 = np.clip(np.rint(L), 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(u8, "L").filter(ImageFilter.MedianFilter(size))).astype(np.float32)


def autocorr(a, mask):
    h, w = a.shape
    F = np.fft.fft2((a - a[mask].mean()) * mask)
    A = np.fft.fftshift(np.abs(np.fft.ifft2(F * np.conj(F))).real)
    return A


def subpixel_peak(A, cx, cy, dx0, dy0):
    """在 (dx0,dy0) 邻域 3×3 做抛物线插值，返回亚像素峰位与峰强。"""
    pts = []
    for dy in (dy0 - 1, dy0, dy0 + 1):
        for dx in (dx0 - 1, dx0, dx0 + 1):
            pts.append(((dx, dy), A[cy + dy, cx + dx]))
    d = dict(pts)
    z0 = d[(dx0, dy0)]
    zx1 = d.get((dx0 + 1, dy0), 0)
    zx0 = d.get((dx0 - 1, dy0), 0)
    zy1 = d.get((dx0, dy0 + 1), 0)
    zy0 = d.get((dx0, dy0 - 1), 0)

    def parab(zm, z0, zp):
        den = zm - 2 * z0 + zp
        if abs(den) < 1e-9 or den > 0:
            return 0.0
        return float(np.clip(0.5 * (zm - zp) / den, -1.0, 1.0))

    subx = parab(zx0, z0, zx1)
    suby = parab(zy0, z0, zy1)
    return dx0 + subx, dy0 + suby, z0


def fold_fine(res, mask, b1, b2, phase, n1f=8, n2f=8):
    """以 (n1f×n2f) 细分格折叠：返回 n1×n2 展示格（每细格平均）。"""
    Bm = np.array([b1, b2])
    invB = np.linalg.inv(Bm)
    ys, xs = np.nonzero(mask)
    coords = np.stack([xs, ys], 1).astype(np.float64)
    uv = coords @ invB.T - np.array(phase)
    fu = uv[:, 0] - np.floor(uv[:, 0])
    fv = uv[:, 1] - np.floor(uv[:, 1])
    n1 = int(round(np.hypot(*b1)))
    n2 = int(round(np.hypot(*b2)))
    bu = np.clip((fu * n1 * n1f).astype(int), 0, n1 * n1f - 1)
    bv = np.clip((fv * n2 * n2f).astype(int), 0, n2 * n2f - 1)
    cell_sum = np.zeros((n2 * n2f, n1 * n1f))
    cell_cnt = np.zeros((n2 * n2f, n1 * n1f))
    np.add.at(cell_sum, (bv, bu), res[ys, xs])
    np.add.at(cell_cnt, (bv, bu), 1.0)
    cell = cell_sum / np.maximum(cell_cnt, 1)
    return cell, cell_cnt


def show_cell(cell, cnt, step, title, min_cnt=4.0):
    print(f"  [{title}]")
    sel = cnt >= min_cnt
    if not sel.any():
        print("   （无稠密格）")
        return
    cs = np.percentile(cell[sel], [2, 98])
    chars = " .:-=+*#%@"
    for r in range(0, cell.shape[0], step):
        row = ""
        for c in range(0, cell.shape[1], step):
            if cnt[r, c] < min_cnt:
                row += "?"
                continue
            v = (cell[r, c] - cs[0]) / max(1e-6, cs[1] - cs[0])
            row += chars[int(np.clip(v, 0, 0.999) * len(chars))]
        print("   " + row)


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "1.png"
    C = 48
    L, alpha = load_luma(BASE / name)
    h, w = L.shape
    mask = np.zeros_like(alpha, dtype=bool)
    mask[0:C, 0:C] = True
    mask[0:C, w - C : w] = True
    mask[h - C : h, 0:C] = True
    mask[h - C : h, w - C : w] = True
    res = L - med(L, 21)

    tiles = [
        res[0:C, 0:C],
        res[0:C, w - C : w],
        res[h - C : h, 0:C],
        res[h - C : h, w - C : w],
    ]
    big = np.zeros((2 * C + 4, 2 * C + 4), dtype=np.float32)
    big[0:C, 0:C] = tiles[0]
    big[0:C, C + 4 : 2 * C + 4] = tiles[1]
    big[C + 4 : 2 * C + 4, 0:C] = tiles[2]
    big[C + 4 : 2 * C + 4, C + 4 : 2 * C + 4] = tiles[3]
    bmask = np.zeros_like(big, dtype=bool)
    bmask[0:C, 0:C] = True
    bmask[0:C, C + 4 : 2 * C + 4] = True
    bmask[C + 4 : 2 * C + 4, 0:C] = True
    bmask[C + 4 : 2 * C + 4, C + 4 : 2 * C + 4] = True

    A = autocorr(big, bmask)
    cy = cx = big.shape[0] // 2
    # 找基向量（含亚像素）
    vecs = []
    for (dx0, dy0) in [(26, 0), (25, 0), (27, 0), (0, 26), (0, 25), (0, 27), (13, 0), (-13, 0), (0, 13), (0, -13)]:
        dx, dy, z = subpixel_peak(A, cx, cy, dx0, dy0)
        vecs.append((z, dx, dy))
    vecs.sort(reverse=True)
    for z, dx, dy in vecs[:8]:
        print(f"  峰 (dx={dx:+.3f}, dy={dy:+.3f})  |v|={np.hypot(dx,dy):.3f}  峰值={z:.3e}")

    # 用最强非平行两峰定基，并做参数精修（在 ±0.3 邻域网格找折叠方差最大）
    basis = []
    for z, dx, dy in vecs:
        v = np.array([dx, dy])
        if all(abs(v[0] * b[1] - v[1] * b[0]) > 50 for b in basis):
            basis.append(v)
        if len(basis) == 2:
            break
    b1, b2 = basis
    print(f"  初步基: b1=({b1[0]:.3f},{b1[1]:.3f}) b2=({b2[0]:.3f},{b2[1]:.3f})")
    if b1[1] == 0 and b2[0] == 0:
        pass

    best = None
    for e1x in np.arange(-0.4, 0.41, 0.1):
        for e1y in np.arange(-0.4, 0.41, 0.1):
            for e2x in np.arange(-0.4, 0.41, 0.1):
                for e2y in np.arange(-0.4, 0.41, 0.1):
                    bb1 = b1 + np.array([e1x, e1y])
                    bb2 = b2 + np.array([e2x, e2y])
                    cell, cnt = fold_fine(res, bmask, bb1, bb2, (0, 0), 4, 4)
                    var = np.var(cell[cnt >= 3]) if (cnt >= 3).any() else 0.0
                    if best is None or var > best[0]:
                        best = (var, bb1, bb2)
    var, bb1, bb2 = best
    print(f"  精修基: b1=({bb1[0]:.3f},{bb1[1]:.3f}) b2=({bb2[0]:.3f},{bb2[1]:.3f})  折叠方差={var:.3f}")

    # 相位优化
    bestp = None
    for p1 in np.arange(0, 1.0, 0.05):
        for p2 in np.arange(0, 1.0, 0.05):
            cell, cnt = fold_fine(res, bmask, bb1, bb2, (p1, p2), 4, 4)
            var = np.var(cell[cnt >= 3]) if (cnt >= 3).any() else 0.0
            if bestp is None or var > bestp[0]:
                bestp = (var, p1, p2)
    _, p1, p2 = bestp
    print(f"  相位: ({p1:.2f},{p2:.2f})  折叠方差={bestp[0]:.3f}")

    cell, cnt = fold_fine(res, bmask, bb1, bb2, (p1, p2), 1, 1)
    show_cell(cell, cnt, 1, f"{name} 折叠字形（26×26）", min_cnt=4.0)


if __name__ == "__main__":
    main()
