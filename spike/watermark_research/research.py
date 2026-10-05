"""水印域测绘 v1（W3.1）：点阵几何 / 幅度 / 覆盖率（开发用）。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def find_repo() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "koutu").is_dir() and (parent / "golden").is_dir():
            return parent
    raise RuntimeError("repo not found")


REPO = find_repo()
BASE = REPO / "golden" / "baseline_products" / "底图"
SIZE = 256


def load_luma(path: Path):
    rgba = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
    rgb = rgba[..., :3]
    L = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return L, rgba[..., 3]


def box_mean(a: np.ndarray, k: int) -> np.ndarray:
    c = np.cumsum(np.cumsum(a, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    y0 = np.clip(np.arange(h) - (k // 2), 0, None)
    y1 = np.clip(np.arange(h) - (k // 2) + k, 0, h)
    x0 = np.clip(np.arange(w) - (k // 2), 0, None)
    x1 = np.clip(np.arange(w) - (k // 2) + k, 0, w)
    s = c[y1][:, x1] - c[y0][:, x1] - c[y1][:, x0] + c[y0][:, x0]
    n = (y1 - y0)[:, None] * (x1 - x0)[None, :]
    return s / n


def find_flat_window(L: np.ndarray, mask: np.ndarray, size: int = SIZE, step: int = 16):
    h, w = L.shape
    best = None
    for y in range(0, h - size + 1, step):
        for x in range(0, w - size + 1, step):
            m = mask[y : y + size, x : x + size]
            if m.mean() < 0.999:
                continue
            sub = L[y : y + size, x : x + size]
            grad = np.abs(np.diff(sub, axis=0)).mean() + np.abs(np.diff(sub, axis=1)).mean()
            if best is None or grad < best[0]:
                best = (grad, y, x)
    return best


def main() -> None:
    names = sys.argv[1:] if len(sys.argv) > 1 else ["1.png", "3.png", "6.png"]
    for name in names:
        L, alpha = load_luma(BASE / name)
        mask = alpha > 240
        print(f"\n===== {name}  尺寸 {L.shape}  有效像素 {mask.mean():.1%} =====")
        found = find_flat_window(L, mask)
        if found is None:
            print("  找不到完全有效的窗口")
            continue
        grad, y, x = found
        sub = L[y : y + SIZE, x : x + SIZE]
        print(f"  最平坦窗口: ({x},{y}) 梯度均值={grad:.3f}")
        base = box_mean(sub, 15)
        res = sub - base
        print(f"  残差: std={res.std():.3f}  min={res.min():.2f}  max={res.max():.2f}")

        win = np.hanning(SIZE)[:, None] * np.hanning(SIZE)[None, :]
        F = np.fft.fftshift(np.fft.fft2(res * win))
        mag = np.abs(F)
        cy = cx = SIZE // 2
        yy, xx = np.mgrid[0:SIZE, 0:SIZE]
        r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        mag2 = mag.copy()
        mag2[(r < 5) | (r > 50)] = 0
        flat = mag2.ravel()
        top = np.argsort(flat)[::-1][:16]
        print("  FFT 峰：")
        for t in top:
            py, px = divmod(int(t), SIZE)
            dyy, dxx = py - cy, px - cx
            rr = np.hypot(dyy, dxx)
            if rr == 0:
                continue
            period = SIZE / rr
            ang = np.degrees(np.arctan2(dyy, dxx)) % 180
            print(f"    (kx={dxx:+4d}, ky={dyy:+4d})  周期={period:6.2f}px  角度={ang:6.1f}°  幅值={mag[py, px]:.0f}")

        seg = res[80:176, 80:176]
        lo, hi = np.percentile(seg, [5, 95])
        chars = " .:-=+*#%@"
        print("  残差视图（96×96，5–95 分位，每行隔 3 采样 2）：")
        for ry in range(0, 96, 3):
            row = ""
            for rx in range(0, 96, 2):
                v = (seg[ry, rx] - lo) / max(1e-6, hi - lo)
                row += chars[int(np.clip(v, 0, 0.999) * len(chars))]
            print("   " + row)


if __name__ == "__main__":
    main()
