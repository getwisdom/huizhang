"""水印域测绘 v4（W3.1）：NCC² 自相关找点阵基，再折叠验证。"""

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
    k = templ.shape[0]
    t = templ - templ.mean()
    n = float(k * k)
    s1 = box_sum(res, k)
    s2 = box_sum(res * res, k)
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


def autocorr_peaks(a: np.ndarray, rmin: int = 12, rmax: int = 80, n: int = 18):
    h, w = a.shape
    F = np.fft.fft2(a - a.mean())
    A = np.fft.fftshift(np.abs(np.fft.ifft2(F * np.conj(F))).real)
    cy, cx = h // 2, w // 2
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    A[(r < rmin) | (r > rmax)] = 0
    # 局部最大
    peaks = []
    flat = A.ravel()
    order = np.argsort(flat)[::-1]
    for idx in order[:4000]:
        v = flat[idx]
        if len(peaks) >= n:
            break
        y, x = divmod(int(idx), w)
        if v <= 0:
            break
        ok = True
        for (px_, py_, _v) in peaks:
            if (px_ - x) ** 2 + (py_ - y) ** 2 < 8 * 8:
                ok = False
                break
        if ok:
            peaks.append((x, y, v))
    return [(x, y, v) for (x, y, v) in peaks]


def fold_and_show(res: np.ndarray, mask: np.ndarray, b1, b2, title: str, n1=None, n2=None):
    b1 = np.asarray(b1, dtype=np.float64)
    b2 = np.asarray(b2, dtype=np.float64)
    Bm = np.array([b1, b2])
    det = b1[0] * b2[1] - b1[1] * b2[0]
    if abs(det) < 20:
        print(f"  [{title}] 基向量近平行，跳过")
        return None
    invB = np.linalg.inv(Bm)
    ys, xs = np.nonzero(mask)
    coords = np.stack([xs, ys], axis=1).astype(np.float64)
    uv = coords @ invB.T
    n1 = n1 or int(round(np.hypot(*b1)))
    n2 = n2 or int(round(np.hypot(*b2)))
    fu = uv[:, 0] - np.floor(uv[:, 0])
    fv = uv[:, 1] - np.floor(uv[:, 1])
    bu = np.clip((fu * n1).astype(int), 0, n1 - 1)
    bv = np.clip((fv * n2).astype(int), 0, n2 - 1)
    cell_sum = np.zeros((n2, n1))
    cell_cnt = np.zeros((n2, n1))
    np.add.at(cell_sum, (bv, bu), res[ys, xs])
    np.add.at(cell_cnt, (bv, bu), 1.0)
    cell = cell_sum / np.maximum(cell_cnt, 1)
    # 显著性：折叠后细胞的“结构”与噪声底的比值
    noise = np.std(res[ys, xs]) / np.sqrt(max(1.0, cell_cnt.mean()))
    sig = np.std(cell) / max(1e-6, noise)
    print(f"  [{title}] b1={np.round(b1,2)} b2={np.round(b2,2)}  折叠结构显著性≈{sig:.2f}σ")
    cs = np.percentile(cell, [2, 98])
    chars = " .:-=+*#%@"
    for r in range(0, n2):
        row = ""
        for c in range(0, n1):
            v = (cell[r, c] - cs[0]) / max(1e-6, cs[1] - cs[0])
            row += chars[int(np.clip(v, 0, 0.999) * len(chars))]
        print("   " + row)
    return sig


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "1.png"
    L, alpha = load_luma(BASE / name)
    mask = alpha > 240
    res = L - med(L, 21)
    ncc = ncc_map(res, gaussian(21, 4.4))
    ncc[~mask] = 0.0

    pos = np.clip(ncc, 0, None) ** 2
    print(f"== {name} ==")
    print("NCC² 自相关峰（(dx,dy), 值）：")
    peaks = autocorr_peaks(pos * mask)
    for (x, y, v) in peaks[:14]:
        h, w = res.shape
        dx, dy = x - w // 2, y - h // 2
        if dy < 0 or (dy == 0 and dx < 0):
            continue
        print(f"  ({dx:+d},{dy:+d})  |v|={v:.3e}  长度={np.hypot(dx,dy):.1f}  角度={np.degrees(np.arctan2(dy,dx))%180:.1f}°")

    # 尝试几组候选基
    tried = []
    cand = []
    for (x, y, v) in peaks:
        h, w = res.shape
        dx, dy = x - w // 2, y - h // 2
        if dy < 0 or (dy == 0 and dx < 0):
            continue
        d = np.hypot(dx, dy)
        if 15 <= d <= 60:
            cand.append((v, dx, dy))
    cand.sort(reverse=True)
    basis = []
    for _v, dx, dy in cand:
        vec = np.array([dx, dy], dtype=np.float64)
        byv = np.array([-dy, dx], dtype=np.float64)
        if all(abs(vec @ b) > 4 and abs(byv @ b) > 4 and abs(vec @ np.array([b[1], -b[0]])) > 4 for b in basis):
            basis.append(vec)
        if len(basis) >= 2:
            break
    if len(basis) == 2:
        sig = fold_and_show(res, mask, basis[0], basis[1], "自相关基")
    # 正交 27 反射对照
    fold_and_show(res, mask, (27, 0), (0, 27), "27正交")
    # 斜向对角对照（19,19）
    fold_and_show(res, mask, (19.0, 19.0), (-19.0, 19.0), "对角 19√2")


if __name__ == "__main__":
    main()
