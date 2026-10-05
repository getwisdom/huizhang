"""核拟合 v3（开发用）：灰底脉冲（含负瓣）数据上的家族拟合 + 逐相单位和检查。"""

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


def kernel_sum(fn, s, taps=(-1, 0, 1, 2)):
    arr = np.array([s - k for k in taps], dtype=np.float64)
    return float(np.sum(fn(arr)))


def main() -> None:
    print(f"点数 = {len(PTS)}")
    cands = []
    for a in np.arange(-1.5, 0.51, 0.05):
        cands.append((f"keys(a={a:.2f})", lambda t, a=a: keys(t, a)))
    for B in np.arange(0.0, 1.51, 0.05):
        for C in np.arange(0.0, 1.51, 0.05):
            cands.append((f"mitchell(B={B:.2f},C={C:.2f})", lambda t, B=B, C=C: mitchell(t, B, C)))

    res = []
    for name, fn in cands:
        v = fn(T)
        err = float(np.mean(np.abs(v - V)))
        mx = float(np.max(np.abs(v - V)))
        res.append((err, mx, name, fn))
    res.sort(key=lambda r: r[0])
    print("前 12 名（按平均误差）：")
    for err, mx, name, _ in res[:12]:
        print(f"  mean={err:.5f} max={mx:.5f}  {name}")

    print("\n前 3 名的逐相单位和 Σ（应≈1）：")
    for err, mx, name, fn in res[:3]:
        sums = [kernel_sum(fn, s) for s in (0.0, 0.25, 0.5, 0.75)]
        fsums = [kernel_sum(fn, s, taps=(-2, -1, 0, 1, 2, 3)) for s in (0.0, 0.25, 0.5, 0.75)]
        print(f"  {name}: Σ4={['%.4f' % x for x in sums]} Σ6={['%.4f' % x for x in fsums]}")

    print("\n冠军逐点对照（含负瓣）：")
    err, mx, name, fn = res[0]
    for (t, m), p in sorted(zip(PTS.tolist(), fn(T).tolist())):
        if abs(t) <= 1.6:
            print(f"  t={t:+.3f}  measured={m:+.4f}  pred={p:+.4f}  diff={p - m:+.4f}")


if __name__ == "__main__":
    main()
