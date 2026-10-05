"""排版合成参数校准（开发用脚本，不参与 pytest 收集）。

对照 `golden/baseline_products/已排版/第1页.png`，在单个槽位区域上尝试不同的
像素对齐约定 / 三次卷积参数 / 预乘设置 / 取整方式，输出差异表供选择。
"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from koutu.core import imaging, layout  # noqa: E402


def main() -> None:
    demo = REPO / "排版demo.png"
    golden_base = REPO / "golden" / "baseline_products" / "底图"
    page = imaging.load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
    template = imaging.load_rgb(demo)
    slots = layout.detect_slots(template)
    print("slots:", len(slots), [(round(s.cx, 2), round(s.cy, 2), round(s.r, 2)) for s in slots[:4]])
    infos, skipped = layout.load_base_infos(golden_base)
    print("bases:", [i.name for i in infos], "skipped:", skipped)

    slot = slots[0]
    info = infos[0]
    print("校准槽位:", (slot.cx, slot.cy, slot.r), "底图:", info.name)

    results = []
    for conv in ("edge", "center"):
        for a in (-0.5, -0.75, -1.0):
            for premult in (False, True):
                for rnd in ("half_up", "half_even"):
                    patch, (px0, py0) = layout._render_slot_patch(
                        slot, info, convention=conv, a=a, premult=premult, rounding=rnd
                    )
                    ph, pw = patch.shape[0], patch.shape[1]
                    g = page[py0 : py0 + ph, px0 : px0 + pw, :3]
                    d = np.abs(patch.astype(np.int16) - g.astype(np.int16))
                    gt8 = int((d.max(axis=2) > 8).sum())
                    results.append(
                        {
                            "gt8": gt8,
                            "mean": float(d.mean()),
                            "max": int(d.max()),
                            "conv": conv,
                            "a": a,
                            "premult": premult,
                            "round": rnd,
                        }
                    )
    results.sort(key=lambda r: (r["gt8"], r["mean"]))
    total = patch.shape[0] * patch.shape[1]
    print(f"区域像素 = {total}")
    for r in results:
        print(
            f"gt8={r['gt8']:>7} ({r['gt8'] / total:.4%})  mean={r['mean']:.4f}  max={r['max']:>3}  "
            f"conv={r['conv']}  a={r['a']}  premult={r['premult']}  round={r['round']}"
        )


if __name__ == "__main__":
    main()
