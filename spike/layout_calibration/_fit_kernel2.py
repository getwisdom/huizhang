"""核拟合 v2（开发用）：带增益/拉伸的参数化家族优化。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")


def gray(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 0].astype(np.float64) / 255.0


def build_points():
    pts = []
    for _tag, path, scale, center_col in (
        ("s10", TEMP / "impulse_s10.png", 10.0, 16),
        ("s2", TEMP / "impulse_s2.png", 2.0, 16),
    ):
        img = gray(path)
        row = img[img.shape[0] // 2]
        cc = (center_col + 0.5) * scale
        for px in range(int(cc - 2.2 * scale), int(cc + 2.2 * scale) + 1):
            t = (px + 0.5) / scale - (center_col + 0.5)
            pts.append((t, row[px]))
    return np.array(pts)


PTS = build_points()
T = PTS[:, 0]
V = PTS[:, 1]


def keys(t, a):
    t = np.abs(t)
    out = np.zeros_like(t)
    m1 = t <= 1
    m2 = (t > 1) & (t < 2)
    out[m1] = (a + 2) * t[m1] ** 3 - (a + 3) * t[m1] ** 2 + 1
    out[m2] = a * t[m2] ** 3 - 5 * a * t[m2] ** 2 + 8 * a * t[m2] - 4 * a
    return out


def mitchell(t, B, C):
    t = np.abs(t)
    out = np.zeros_like(t)
    m1 = t < 1
    m2 = (t >= 1) & (t < 2)
    out[m1] = ((12 - 9 * B - 6 * C) * t[m1] ** 3 + (-18 + 12 * B + 6 * C) * t[m1] ** 2 + (6 - 2 * B)) / 6
    out[m2] = (
        (-B - 6 * C) * t[m2] ** 3
        + (6 * B + 30 * C) * t[m2] ** 2
        + (-12 * B - 48 * C) * t[m2]
        + (8 * B + 24 * C)
    ) / 6
    return out


def fit_with_gain(raw_fn, ts, vs):
    f = raw_fn(ts)
    denom = float(np.dot(f, f))
    if denom <= 1e-12:
        return 1e9, 0.0
    g = float(np.dot(vs, f) / denom)
    err = float(np.mean(np.abs(g * f - vs)))
    return err, g


def main() -> None:
    print(f"点数 = {len(PTS)}")
    best = []

    # A: 拉伸的 keys 家族（带线性增益）
    for a in np.arange(-1.5, 0.55, 0.05):
        for s in np.arange(0.70, 1.45, 0.01):
            err, g = fit_with_gain(lambda tt, a=a, s=s: keys(tt * s, a), T, V)
            best.append((err, f"keys(a={a:.2f}) s={s:.2f} g={g:.3f}"))

    # B: 拉伸的 mitchell 家族（带线性增益）
    for B in np.arange(0.0, 1.2, 0.05):
        for C in np.arange(0.0, 1.2, 0.05):
            for s in np.arange(0.80, 1.25, 0.025):
                err, g = fit_with_gain(lambda tt, B=B, C=C, s=s: mitchell(tt * s, B, C), T, V)
                best.append((err, f"mitchell(B={B:.2f},C={C:.2f}) s={s:.3f} g={g:.3f}"))

    # C: 高斯（带增益）
    for sigma in np.arange(0.30, 0.95, 0.01):
        err, g = fit_with_gain(lambda tt, sigma=sigma: np.exp(-(tt**2) / (2 * sigma * sigma)), T, V)
        best.append((err, f"gauss(sig={sigma:.2f}) g={g:.3f}"))

    best.sort(key=lambda x: x[0])
    print("前 12 名：")
    for err, desc in best[:12]:
        print(f"  err={err:.5f}  {desc}")

    # 对冠军做分区残差 + 单位分解检查
    print("\n冠军在部分 t 点的对照：")
    winner = best[0][1]
    print(" winner:", winner)


if __name__ == "__main__":
    main()
