"""水印域测绘 v3（W3.1）：NCC 检测印记 → 拟合点阵基向量 → 折叠字形。"""

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
    L = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return L, rgba[..., 3]


def med(L: np.ndarray, size: int) -> np.ndarray:
    u8 = np.clip(np.rint(L), 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(u8, "L").filter(ImageFilter.MedianFilter(size))).astype(np.float32)


def gaussian(size: int, sigma: float) -> np.ndarray:
    c = (size - 1) / 2.0
    yy, xx = np.mgrid[0:size, 0:size]
    g = np.exp(-((xx - c) ** 2 + (yy - c) ** 2) / (2 * sigma * sigma))
    return g / g.sum()


def box_sum(a: np.ndarray, k: int) -> np.ndarray:
    c = np.cumsum(np.cumsum(a, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    y0 = np.clip(np.arange(h) - (k // 2), 0, None)
    y1 = np.clip(np.arange(h) - (k // 2) + k, 0, h)
    x0 = np.clip(np.arange(w) - (k // 2), 0, None)
    x1 = np.clip(np.arange(w) - (k // 2) + k, 0, w)
    return c[y1][:, x1] - c[y0][:, x1] - c[y1][:, x0] + c[y0][:, x0]


def ncc_map(res: np.ndarray, templ: np.ndarray) -> np.ndarray:
    """按模板中心索引的近似 NCC（局部去均值，逐点归一）。"""
    k = templ.shape[0]
    t = templ - templ.mean()
    n = float(k * k)
    # 局部和
    s1 = box_sum(res, k)
    s2 = box_sum(res * res, k)
    # 与零均值模板的相关 = Σ res*t = Σ (res - mean)*t
    from numpy.lib.stride_tricks import sliding_window_view

    win = sliding_window_view(res, (k, k))
    num = np.einsum("ijkl,kl->ij", win, t.astype(np.float32), optimize=True)
    var = s2 - s1 * s1 / n
    denom = np.sqrt(np.maximum(var, 1e-6) * float((t * t).sum()))
    out = np.zeros(res.shape, dtype=np.float32)
    off = k // 2
    hh, ww = res.shape
    out[off : hh - off, off : ww - off] = num / denom[off : hh - off, off : ww - off]
    return out


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "1.png"
    L, alpha = load_luma(BASE / name)
    mask = alpha > 240
    res = L - med(L, 21)
    tmpl = gaussian(21, 4.4)
    ncc = ncc_map(res, tmpl)
    ncc[~mask] = 0.0

    # 收集显著印记（局部最大且 NCC 高）
    thresh = 0.45
    order = np.argsort(ncc.ravel())[::-1]
    marks = []
    min_sep = 10
    for idx in order[:20000]:
        v = ncc.ravel()[idx]
        if v < thresh or len(marks) >= 400:
            break
        y, x = divmod(int(idx), ncc.shape[1])
        ok = True
        for (mx, my) in marks:
            if (mx - x) ** 2 + (my - y) ** 2 < min_sep * min_sep:
                ok = False
                break
        if ok:
            marks.append((x, y))
    print(f"{name}: NCC 峰值={ncc.max():.3f}  印记数(>{thresh})={len(marks)}")
    if len(marks) < 8:
        print("  印记太少")
        return

    # 差分向量统计（找最短基向量）
    pts = np.array(marks, dtype=np.float64)
    diffs = []
    for i in range(len(pts)):
        for j in range(len(pts)):
            if i == j:
                continue
            d = pts[j] - pts[i]
            if 0 < np.hypot(*d) < 60:
                diffs.append(d)
    diffs = np.array(diffs)
    # 角度直方图（0..360 每 5°）→ 主方向
    ang = np.degrees(np.arctan2(diffs[:, 1], diffs[:, 0])) % 360
    hist = np.histogram(ang, bins=72, range=(0, 360))[0]
    main_dirs = np.argsort(hist)[::-1][:6]
    print("  差分向量主方向（5° 桶）:", [(int(d) * 5, int(hist[d])) for d in main_dirs])

    # 在每个主方向桶内估计长度众数
    for d in main_dirs[:3]:
        sel = (ang >= d * 5 - 2.5) & (ang < d * 5 + 2.5)
        if sel.sum() < 5:
            continue
        lens = np.hypot(diffs[sel, 0], diffs[sel, 1])
        med_len = np.median(lens)
        print(f"    方向 {d*5}°: 计数={sel.sum()}  长度中位={med_len:.2f}")

    # 用主方向对构造基向量（取前两个不同方向）
    def unit_vec(deg):
        r = np.radians(deg)
        return np.array([np.cos(r), np.sin(r)])

    basis = []
    for d in main_dirs:
        if len(basis) >= 2:
            break
        sel = (ang >= d * 5 - 2.5) & (ang < d * 5 + 2.5)
        if sel.sum() < 8:
            continue
        lens = np.hypot(diffs[sel, 0], diffs[sel, 1])
        L0 = np.median(lens)
        v = unit_vec(d * 5) * L0
        # 与已有基向量不平行才接受
        if all(abs(np.cross(v, b)) > 5.0 for b in basis):
            basis.append(v)
    print("  拟合基向量:", [tuple(np.round(b, 2)) for b in basis])

    if len(basis) == 2:
        B = np.array(basis).T  # 列向量
        invB = np.linalg.inv(B)
        p0 = pts[np.argmax([ncc[int(p[1]), int(p[0])] for p in pts])]
        rel = (pts - p0) @ invB.T  # 每个印记的基坐标
        frac = rel - np.round(rel)
        print(f"  相对原点 {tuple(p0)} 的基坐标相位: x {np.mean(frac[:,0]):+.3f}±{np.std(frac[:,0]):.3f}, "
              f"y {np.mean(frac[:,1]):+.3f}±{np.std(frac[:,1]):.3f}")

    # 折叠（正交假设 pitch=27 与数据驱动基都试）
    for label, bvecs in [("27正交", [np.array([27.0, 0]), np.array([0, 27.0])])] + (
        [("数据基", basis)] if len(basis) == 2 else []
    ):
        b1, b2 = bvecs
        Bm = np.array([b1, b2])
        try:
            invB = np.linalg.inv(Bm)
        except np.linalg.LinAlgError:
            continue
        h, w = res.shape
        ys, xs = np.nonzero(mask)
        coords = np.stack([xs - 0.0, ys - 0.0], axis=1).astype(np.float64)
        uv = coords @ invB.T
        fu = np.mod(uv[:, 0] + 0.5, 1.0) - 0.5
        fv = np.mod(uv[:, 1] + 0.5, 1.0) - 0.5
        n1 = int(round(np.hypot(*b1)))
        n2 = int(round(np.hypot(*b2)))
        bu = np.clip(np.floor((fu + 0.5) * n1).astype(int), 0, n1 - 1)
        bv = np.clip(np.floor((fv + 0.5) * n2).astype(int), 0, n2 - 1)
        cell_sum = np.zeros((n2, n1))
        cell_cnt = np.zeros((n2, n1))
        np.add.at(cell_sum, (bv, bu), res[ys, xs])
        np.add.at(cell_cnt, (bv, bu), 1.0)
        cell = cell_sum / np.maximum(cell_cnt, 1)
        print(f"\n  折叠细胞（{label}）：{n1}×{n2}，样本/格 ≈{int(cell_cnt.mean())}")
        cs = np.percentile(cell, [2, 98])
        chars = " .:-=+*#%@"
        for r in range(0, n2, 1):
            row = ""
            for c in range(0, n1, 1):
                v = (cell[r, c] - cs[0]) / max(1e-6, cs[1] - cs[0])
                row += chars[int(np.clip(v, 0, 0.999) * len(chars))]
            print("   " + row)


if __name__ == "__main__":
    main()
