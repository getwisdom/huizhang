"""核拟合 v4（开发用）：拉伸 mitchell / keys 家族最终拟合 + 全表输出。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")


def gray(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 0].astype(np.float64)


def build_points():
    pts = []
    for _tag, path, scale, center_col in (
        ("g10", TEMP / "impulse_gray_s10.png", 10.0, 16),
        ("g2", TEMP / "impulse_gray_s2.png", 2.0, 16),
    ):
        img = gray(path)
        row = img[img.shape[0] // 2]
        cc = (center_col + 0.5) * scale
        for px in range(int(cc - 2.6 * scale), int(cc + 2.6 * scale) + 1):
            t = (px + 0.5) / scale - (center_col + 0.5)
            k = (row[px] - 128.0) / 127.0
            pts.append((t, k))
    return np.array(pts)


PTS = build_points()
T = PTS[:, 0]
V = PTS[:, 1]


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


def keys(t, a):
    t = np.abs(t)
    out = np.zeros_like(t)
    m1 = t <= 1
    m2 = (t > 1) & (t < 2)
    out[m1] = (a + 2) * t[m1] ** 3 - (a + 3) * t[m1] ** 2 + 1
    out[m2] = a * t[m2] ** 3 - 5 * a * t[m2] ** 2 + 8 * a * t[m2] - 4 * a
    return out


def main() -> None:
    print(f"点数 = {len(PTS)}")
    print("\n全表（合并两侧，t 升序）：")
    for t, v in sorted(zip(T.tolist(), V.tolist())):
        print(f"  t={t:+.3f}  K={v:+.4f}")

    best = []
    for B in np.arange(0.30, 0.56, 0.025):
        for C in np.arange(0.50, 0.91, 0.025):
            for s in np.arange(1.00, 1.36, 0.01):
                v = mitchell(T * s, B, C)
                best.append((float(np.mean(np.abs(v - V))), f"mitchell(B={B:.3f},C={C:.3f}) s={s:.2f}"))
    for a in np.arange(-1.2, 0.21, 0.025):
        for s in np.arange(1.00, 1.61, 0.01):
            v = keys(T * s, a)
            best.append((float(np.mean(np.abs(v - V))), f"keys(a={a:.3f}) s={s:.2f}"))
    best.sort(key=lambda x: x[0])
    print("\n前 12 名：")
    for e, d in best[:12]:
        print(f"  mean={e:.5f}  {d}")


if __name__ == "__main__":
    main()
