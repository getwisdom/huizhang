"""核拟合 v5（开发用）：mitchell/keys ⊛ box 家族定形（每候选一次卷积）。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")

_DT = 0.002
_U = np.arange(-3.0, 3.0 + _DT, _DT)


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
            pts.append((t, (row[px] - 128.0) / 127.0))
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


def conv_box(raw_full, w):
    box = np.where(np.abs(_U) <= w / 2, 1.0 / w, 0.0)
    conv = np.convolve(raw_full, box, mode="same") * _DT
    return conv


def main() -> None:
    print(f"点数 = {len(PTS)}")
    best = []
    for B in np.arange(0.25, 0.56, 0.025):
        for C in np.arange(0.50, 0.91, 0.025):
            raw = mitchell(_U, B, C)
            for w in np.arange(0.30, 0.91, 0.05):
                conv = conv_box(raw, w)
                v = np.interp(T, _U, conv)
                best.append((float(np.mean(np.abs(v - V))), f"mitchell(B={B:.3f},C={C:.3f})⊛box({w:.2f})", (B, C, w)))
    for a in np.arange(-1.2, 0.21, 0.05):
        raw = keys(_U, a)
        for w in np.arange(0.30, 0.91, 0.05):
            conv = conv_box(raw, w)
            v = np.interp(T, _U, conv)
            best.append((float(np.mean(np.abs(v - V))), f"keys(a={a:.2f})⊛box({w:.2f})", (a, w)))
    best.sort(key=lambda x: x[0])
    print("前 12 名：")
    for e, d, _p in best[:12]:
        print(f"  mean={e:.5f}  {d}")

    e, name, params = best[0]
    print(f"\n冠军 {name}  逐点对照：")
    if "mitchell" in name:
        B, C, w = params
        conv = conv_box(mitchell(_U, B, C), w)
    else:
        a, w = params
        conv = conv_box(keys(_U, a), w)
    pred = np.interp(T, _U, conv)
    sums = {}
    for s in (0.0, 0.25, 0.5, 0.75):
        arr = np.array([s - k for k in (-2, -1, 0, 1, 2, 3)])
        sums[s] = float(np.sum(np.interp(arr, _U, conv)))
    print("  逐相 Σ6 =>", {k: round(v, 4) for k, v in sums.items()})
    for (t, m), p in sorted(zip(PTS.tolist(), pred.tolist())):
        print(f"  t={t:+.3f}  measured={m:+.4f}  pred={p:+.4f}  diff={p - m:+.4f}")


if __name__ == "__main__":
    main()
