"""核拟合（开发用）：用脉冲探针数据判定 GDI+ HighQualityBicubic 的真实核。"""

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


def keys(t, a):
    t = np.abs(t)
    out = np.zeros_like(t)
    m1 = t <= 1
    m2 = (t > 1) & (t < 2)
    out[m1] = (a + 2) * t[m1] ** 3 - (a + 3) * t[m1] ** 2 + 1
    out[m2] = a * t[m2] ** 3 - 5 * a * t[m2] ** 2 + 8 * a * t[m2] - 4 * a
    return out


def bsp(t):
    t = np.abs(t)
    out = np.zeros_like(t)
    m1 = t <= 1
    m2 = (t > 1) & (t < 2)
    out[m1] = (3 * t[m1] ** 3 - 6 * t[m1] ** 2 + 4) / 6
    out[m2] = (2 - t[m2]) ** 3 / 6
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


def conv_pair(k1, k2, half=8.0, dt=0.0025):
    x = np.arange(-half, half + dt, dt)
    kc = np.convolve(k1(x), k2(x), mode="same") * dt
    return x, kc


def evaluate(fn):
    v = fn(PTS[:, 0])
    return float(np.mean(np.abs(v - PTS[:, 1]))), float(np.max(np.abs(v - PTS[:, 1])))


def main() -> None:
    print(f"校准点数 = {len(PTS)}")
    cands = []
    for a in (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25):
        cands.append((f"keys({a})", lambda t, a=a: keys(t, a)))
    cands.append(("bsp", bsp))
    for B, C in ((1 / 3, 1 / 3), (1.0, 0.0), (0.0, 0.5), (0.5, 0.5), (0.0, 1.0)):
        cands.append((f"mitchell(B={B:.2f},C={C:.2f})", lambda t, B=B, C=C: mitchell(t, B, C)))
    for s in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70):
        cands.append((f"gauss(s={s})", lambda t, s=s: np.exp(-(t**2) / (2 * s * s))))

    pool = {f"keys({a})": (lambda t, a=a: keys(t, a)) for a in (-1.0, -0.75, -0.5, -0.25, 0.0)}
    pool["bsp"] = bsp
    pool["box0.5"] = lambda t: np.where(np.abs(t) <= 0.25, 1.0, 0.0)
    pool["box1.0"] = lambda t: np.where(np.abs(t) <= 0.5, 1.0, 0.0)
    pool["tri"] = lambda t: np.clip(1 - np.abs(t), 0, None)
    names = list(pool)
    for i, n1 in enumerate(names):
        for n2 in names[i:]:
            x, kc = conv_pair(pool[n1], pool[n2])
            cands.append((f"conv({n1} * {n2})", lambda t, x=x, kc=kc: np.interp(t, x, kc)))

    res = sorted((evaluate(f) + (name,)) for name, f in cands)
    print("候选核（按 mean|err| 升序前 18）：")
    for mean, mx, name in res[:18]:
        print(f"  mean={mean:.5f}  max={mx:.5f}  {name}")

    print("\n实测表 vs 冠军：")
    best_name = res[0][2]
    f = dict(cands)[best_name]
    v = f(PTS[:, 0])
    for (t, m), p in sorted(zip(PTS.tolist(), v.tolist())):
        if abs(t) <= 1.3:
            print(f"  t={t:+.3f}  measured={m:.4f}  pred={p:.4f}  diff={p - m:+.4f}")


if __name__ == "__main__":
    main()
