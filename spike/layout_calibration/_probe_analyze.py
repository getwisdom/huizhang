"""GDI+ 探针分析（开发用）：从 step / impulse / ramp 反推采样约定与卷积核。"""

import sys
from pathlib import Path

import numpy as np

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")
ROW = 80


def load_gray(p: Path) -> np.ndarray:
    from PIL import Image

    return np.asarray(Image.open(p).convert("RGBA"))[..., 0].astype(np.float64)


def k_keys(t: float, a: float) -> float:
    t = abs(t)
    if t <= 1.0:
        return (a + 2) * t**3 - (a + 3) * t**2 + 1
    if t < 2.0:
        return a * t**3 - 5 * a * t**2 + 8 * a * t - 4 * a
    return 0.0


def k_bspline(t: float) -> float:
    t = abs(t)
    if t <= 1.0:
        return (3 * t**3 - 6 * t**2 + 4) / 6
    if t < 2.0:
        return (2 - t) ** 3 / 6
    return 0.0


def main() -> None:
    step = load_gray(TEMP / "probe_step.png")
    imp = load_gray(TEMP / "probe_impulse.png")
    ramp = load_gray(TEMP / "probe_ramp.png")

    print("STEP  row80 x=74..86:", [int(v) for v in step[ROW, 74:87]])
    print("IMPUL row80 x=74..86:", [int(v) for v in imp[ROW, 74:87]])
    print("RAMP  row80 x=74..86:", [int(v) for v in ramp[ROW, 74:87]])

    print("\n=== impulse：t 网格 vs 实测 vs 候选核（255 归一） ===")
    for px in range(74, 87):
        u = px + 0.5
        s_edge = u / 10.0
        for conv in ("edge", "center"):
            s = s_edge - 0.5 if conv == "edge" else s_edge
            t = s - 8.0
            measured = imp[ROW, px] / 255.0 if conv == "edge" else float("nan")
            if conv == "edge":
                cands = {f"a={a}": k_keys(t, a) for a in (-0.5, -0.75, -1.0, 0.0)}
                cands["bsp"] = k_bspline(t)
                cstr = "  ".join(f"{k}:{v:+.3f}" for k, v in cands.items())
                print(f"px={px} t={t:+.3f} 实测={measured:.3f}  {cstr}")

    print("\n=== impulse：各候选核平均绝对误差（edge 约定） ===")
    for name, fn in [
        ("a=-0.5", lambda t: k_keys(t, -0.5)),
        ("a=-0.75", lambda t: k_keys(t, -0.75)),
        ("a=-1.0", lambda t: k_keys(t, -1.0)),
        ("a=0.0", lambda t: k_keys(t, 0.0)),
        ("bspline", k_bspline),
    ]:
        errs = []
        for px in range(74, 87):
            t = (px + 0.5) / 10.0 - 0.5 - 8.0
            errs.append(abs(255.0 * fn(t) - imp[ROW, px]))
        print(f"{name}: mean|err| = {sum(errs) / len(errs):.2f}  max = {max(errs):.1f}")

    print("\n=== step：各候选预测平均绝对误差（edge 约定） ===")
    # 中心帧时源阶跃：src[i]=0(i<8),255(i>=8)；预测值 = 255 * Σ_{i≥8} K(s-i)
    for name, fn in [
        ("a=-0.5", lambda t: k_keys(t, -0.5)),
        ("a=-0.75", lambda t: k_keys(t, -0.75)),
        ("a=-1.0", lambda t: k_keys(t, -1.0)),
        ("a=0.0", lambda t: k_keys(t, 0.0)),
        ("bspline", k_bspline),
    ]:
        errs = []
        for px in range(70, 91):
            s = (px + 0.5) / 10.0 - 0.5
            val = 0.0
            for i in range(0, 16):
                if i >= 8:
                    val += fn(s - i)
            errs.append(abs(255.0 * val - step[ROW, px]))
        pred = [
            round(
                255.0
                * sum(fn((p + 0.5) / 10.0 - 0.5 - i) for i in range(8, 16))
            )
            for p in range(74, 87)
        ]
        print(f"{name}: mean|err| = {sum(errs) / len(errs):.2f}  pred74..86 = {pred}")


if __name__ == "__main__":
    main()
