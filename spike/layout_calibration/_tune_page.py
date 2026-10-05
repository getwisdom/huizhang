"""页面级参数微调（开发用）：(B,C,BOX)、取整、预乘的小网格搜索。"""

import shutil
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import helpers  # noqa: E402
from koutu.core import layout  # noqa: E402

GOLD = helpers.load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
DEMO = REPO / "排版demo.png"
BASE = REPO / "golden" / "baseline_products" / "底图"
WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Administrator\AppData\Local\Temp\koutu_tune")
PAGE_PX = 2480 * 3508


def render(tag: str) -> np.ndarray:
    out = WORK / tag
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    layout.run_layout_batch(DEMO, BASE, out)
    return helpers.load_rgba(out / "第1页.png")


def metric(page: np.ndarray):
    d = np.abs(page[..., :3].astype(np.int16) - GOLD[..., :3].astype(np.int16)).max(axis=2)
    gt8 = int((d > 8).sum())
    big = d > 8
    return gt8, gt8 / PAGE_PX, float(d[big].mean()) if gt8 else 0.0, float(d.mean())


def run(tag: str, **cfg):
    for k, v in cfg.items():
        setattr(layout, k, v)
    layout._GDI_KERNEL_CACHE = None
    m = metric(render(tag))
    print(f"{tag:<34} B={layout.GDI_B:.2f} C={layout.GDI_C:.3f} box={layout.GDI_BOX:.2f} "
          f"rnd={layout.COMPOSITE_ROUND:<9} premult={layout.COMPOSITE_PREMULT}  "
          f"gt8={m[0]:>6} ({m[1]:.4%})  meanDiff>8={m[2]:.1f} meanAll={m[3]:.3f}")
    return m


def main() -> None:
    results = []

    def rec(tag, m):
        results.append((m[0], tag))

    rec("base", run("base"))

    # 取整 / 预乘
    rec("half_even", run("half_even", COMPOSITE_ROUND="half_even"))
    rec("premult", run("premult", COMPOSITE_PREMULT=True))
    rec("premult+even", run("premult_even", COMPOSITE_PREMULT=True, COMPOSITE_ROUND="half_even"))
    # 复位
    layout.COMPOSITE_ROUND = "half_up"
    layout.COMPOSITE_PREMULT = False

    # (B, C, BOX) 网格
    for B in (0.20, 0.25, 0.30):
        for C in (0.850, 0.875, 0.900):
            for BOX in (0.70, 0.75, 0.80):
                tag = f"B{B:.2f}_C{C:.3f}_X{BOX:.2f}"
                rec(tag, run(tag, GDI_B=B, GDI_C=C, GDI_BOX=BOX))

    results.sort()
    print("\n最优 10：")
    for gt8, tag in results[:10]:
        print(f"  gt8={gt8:>6} ({gt8 / PAGE_PX:.4%})  {tag}")


if __name__ == "__main__":
    main()
