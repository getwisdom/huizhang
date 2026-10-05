"""三方全页对照 + 诊断（开发用）：.NET 全页渲染 vs golden vs 我们。"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import helpers  # noqa: E402
from koutu.core import layout  # noqa: E402

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Administrator\AppData\Local\Temp\koutu_probe")
GOLD = helpers.load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
DEMO = REPO / "排版demo.png"
BASE = REPO / "golden" / "baseline_products" / "底图"
PAGE_PX = 2480 * 3508


def build_job() -> dict:
    template = layout.imaging.load_rgb(DEMO)
    slots = layout.detect_slots(template)
    infos, _ = layout.load_base_infos(BASE)
    draws = []
    for i, info in enumerate(infos):
        slot = slots[i]
        draws.append(
            {
                "file": str(info.path.resolve()),
                "sx": float(info.min_x - 1),
                "sy": float(info.min_y - 1),
                "sw": float(info.max_x - info.min_x + 3),
                "sh": float(info.max_y - info.min_y + 3),
                "dx": float(slot.cx - slot.r - 1),
                "dy": float(slot.cy - slot.r - 1),
                "dw": float(2 * slot.r + 2),
                "dh": float(2 * slot.r + 2),
            }
        )
    return {
        "canvasW": template.shape[1],
        "canvasH": template.shape[0],
        "out": str(TEMP / "fullpage_net.png"),
        "draws": draws,
    }


def diff_stats(a, b, label):
    d = np.abs(a[..., :3].astype(np.int16) - b[..., :3].astype(np.int16)).max(axis=2)
    mask = d > 8
    n = int(mask.sum())
    print(f"{label}: gt8={n} ({n / PAGE_PX:.4%})  meanAll={d.mean():.4f}", end="")
    if n:
        vals = d[mask]
        print(
            f"  |Δ|>8: p50={np.percentile(vals, 50):.0f} p90={np.percentile(vals, 90):.0f} max={vals.max()}"
        )
        ys, xs = np.nonzero(mask)
        print(f"  bbox: x {xs.min()}..{xs.max()}  y {ys.min()}..{ys.max()}")
    else:
        print()
    return d, mask


def main() -> None:
    job = build_job()
    (TEMP / "fullpage_job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "tests" / "_gdiplus_fullpage.ps1"),
            "-Ops",
            str(TEMP / "fullpage_job.json"),
        ],
        check=True,
    )
    net = helpers.load_rgba(TEMP / "fullpage_net.png")

    out = TEMP / "ours_w2"
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    layout.run_layout_batch(DEMO, BASE, out)
    ours = helpers.load_rgba(out / "第1页.png")

    print("=== A: .NET 全页 vs golden ===")
    dA, mA = diff_stats(net, GOLD, "net-vs-golden")
    print("=== B: ours vs .NET 全页 ===")
    dB, mB = diff_stats(ours, net, "ours-vs-net")
    print("=== C: ours vs golden ===")
    diff_stats(ours, GOLD, "ours-vs-golden")

    # 按槽分类（B 的差异）
    template = layout.imaging.load_rgb(DEMO)
    slots = layout.detect_slots(template)
    ys, xs = np.nonzero(mB)
    if len(xs):
        px = xs + 0.5
        py = ys + 0.5
        per_slot = np.full(len(slots), -1)
        mind = np.full(len(xs), 1e18)
        for k, s in enumerate(slots):
            dd = np.sqrt((px - s.cx) ** 2 + (py - s.cy) ** 2)
            upd = dd < mind
            mind[upd] = dd[upd]
            per_slot[upd] = k
        print("\nours-vs-net 差异按槽归属（最近槽）：")
        for k in range(len(slots)):
            sel = per_slot == k
            if sel.sum() == 0:
                continue
            near = mind[sel]
            rim = ((near > slots[k].r - 8) & (near < slots[k].r + 8)).sum()
            inner = (near <= slots[k].r - 8).sum()
            corner = (near >= slots[k].r + 8).sum()
            print(f"  槽{k + 1}: 共{sel.sum():>6}  内{inner:>6}  边缘带{rim:>6}  角区{corner:>6}")


if __name__ == "__main__":
    main()
