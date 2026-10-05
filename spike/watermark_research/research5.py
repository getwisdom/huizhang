"""水印域测绘 v6（W3.1）：四角 48×48 纯背景块（圆外）测点阵。"""

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
C = 48


def load_luma(path: Path):
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    rgb = rgba[..., :3].astype(np.float32)
    L = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return L, rgba[..., 3]


def med(L: np.ndarray, size: int) -> np.ndarray:
    u8 = np.clip(np.rint(L), 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(u8, "L").filter(ImageFilter.MedianFilter(size))).astype(np.float32)


def fold(res, mask, b1, b2, title):
    b1 = np.asarray(b1, float)
    b2 = np.asarray(b2, float)
    det = b1[0] * b2[1] - b1[1] * b2[0]
    if abs(det) < 100:
        print(f"  [{title}] 近平行跳过 |det|={abs(det):.0f}")
        return
    invB = np.linalg.inv(np.array([b1, b2]))
    ys, xs = np.nonzero(mask)
    coords = np.stack([xs, ys], 1).astype(float)
    uv = coords @ invB.T
    fu = uv[:, 0] - np.floor(uv[:, 0])
    fv = uv[:, 1] - np.floor(uv[:, 1])
    n1 = int(round(np.hypot(*b1)))
    n2 = int(round(np.hypot(*b2)))
    bu = np.clip((fu * n1).astype(int), 0, n1 - 1)
    bv = np.clip((fv * n2).astype(int), 0, n2 - 1)
    cell_sum = np.zeros((n2, n1))
    cell_cnt = np.zeros((n2, n1))
    np.add.at(cell_sum, (bv, bu), res[ys, xs])
    np.add.at(cell_cnt, (bv, bu), 1.0)
    cell = cell_sum / np.maximum(cell_cnt, 1)
    noise = np.std(res[ys, xs]) / np.sqrt(max(1.0, cell_cnt.mean()))
    print(f"  [{title}] b1={np.round(b1,2)} b2={np.round(b2,2)}  样本/格≈{int(cell_cnt.mean())}  结构≈{np.std(cell)/max(1e-9,noise):.2f}σ  原始std={np.std(res[ys,xs]):.2f}")
    cs = np.percentile(cell, [2, 98])
    chars = " .:-=+*#%@"
    for r in range(n2):
        row = ""
        for c in range(n1):
            v = (cell[r, c] - cs[0]) / max(1e-6, cs[1] - cs[0])
            row += chars[int(np.clip(v, 0, 0.999) * len(chars))]
        print("   " + row)


def main() -> None:
    names = sys.argv[1:] if len(sys.argv) > 1 else ["1.png"]
    for name in names:
        L, alpha = load_luma(BASE / name)
        h, w = L.shape
        mask = np.zeros_like(alpha, dtype=bool)
        mask[0:C, 0:C] = True
        mask[0:C, w - C : w] = True
        mask[h - C : h, 0:C] = True
        mask[h - C : h, w - C : w] = True
        res = L - med(L, 21)
        in_box = res[mask]
        print(f"===== {name}  角区样本 {mask.sum()}  残差std={in_box.std():.2f}  p1={np.percentile(in_box,1):.2f}  p99={np.percentile(in_box,99):.2f}  alpha(max)={alpha[mask].max()} =====")

        # 把四角拼成 2×2 布局的“等效大图”做自相关：直接对掩码内的值做 FFT 不规整，改用拼接
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

        a = (big - big[bmask].mean()) * bmask
        F = np.fft.fft2(a)
        A = np.fft.fftshift(np.abs(np.fft.ifft2(F * np.conj(F))).real)
        cy = cx = big.shape[0] // 2
        peaks = []
        for dy in range(-44, 45):
            for dx in range(-44, 45):
                r = np.hypot(dx, dy)
                if r < 8 or r > 44:
                    continue
                v = A[cy + dy, cx + dx]
                peaks.append((v, dx, dy))
        peaks.sort(reverse=True)
        kept = []
        for v, dx, dy in peaks:
            if all((kx - dx) ** 2 + (ky - dy) ** 2 > 25 for _v, kx, ky in kept):
                kept.append((v, dx, dy))
            if len(kept) >= 8:
                break
        print("  角区自相关峰（去重复）:")
        for v, dx, dy in kept:
            print(f"    (dx={dx:+d},dy={dy:+d}) |v|={np.hypot(dx,dy):.1f} 角度={np.degrees(np.arctan2(dy,dx))%180:.1f}°")

        fold(big, bmask, (27, 0), (0, 27), "27正交")
        fold(big, bmask, (27, 0), (13.5, 23.4), "27+斜向(近似六方)")
        # 数据驱动：取最强两个不平行峰为基
        basis = []
        for v, dx, dy in kept:
            vec = np.array([dx, dy], float)
            ok = True
            for b in basis:
                if abs(vec[0] * b[1] - vec[1] * b[0]) < 100:
                    ok = False
            if ok:
                basis.append(vec)
            if len(basis) == 2:
                break
        if len(basis) == 2:
            fold(big, bmask, basis[0], basis[1], "数据基")


if __name__ == "__main__":
    main()
