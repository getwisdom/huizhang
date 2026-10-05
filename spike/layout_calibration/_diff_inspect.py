"""差异分布检查（开发用）：定位 probe/golden/ours 的差异区域结构。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from koutu.core import imaging, layout  # noqa: E402


def load_rgba(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)


def report(name: str, a: np.ndarray, b: np.ndarray) -> None:
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    mask = d > 8
    ys, xs = np.nonzero(mask)
    print(f"\n== {name}: gt8={mask.sum()} ==")
    if mask.sum() == 0:
        return
    print(f"  bbox: x {xs.min()}..{xs.max()}  y {ys.min()}..{ys.max()}")
    print(f"  diff>8 值分布: p50={np.percentile(d[mask], 50):.0f} p90={np.percentile(d[mask], 90):.0f} max={d.max()}")
    # 16x 下采样热度图（0-9）
    hh, ww = mask.shape
    bh, bw = hh // 16, ww // 16
    heat = mask[: bh * 16, : bw * 16].reshape(bh, 16, bw, 16).sum(axis=(1, 3))
    rows = []
    for r in range(0, bh, max(1, bh // 24)):
        line = "".join("." if heat[r, c] == 0 else ("#" if heat[r, c] > 200 else str(min(9, heat[r, c] // 40 + 1))) for c in range(bw))
        rows.append(line)
    print("  热度图(每格16px):")
    for line in rows:
        print("   " + line)
    for k in range(min(6, len(xs))):
        x, y = int(xs[k]), int(ys[k])
        print(f"  sample ({x},{y}): a={a[y, x, :3].tolist()} b={b[y, x, :3].tolist()}")


def main() -> None:
    page = load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
    probe = load_rgba(TEMP / "probe_slot1.png")
    template = imaging.load_rgb(REPO / "排版demo.png")
    slots = layout.detect_slots(template)
    infos, _ = layout.load_base_infos(REPO / "golden" / "baseline_products" / "底图")
    slot, info = slots[0], infos[0]
    patch, (px0, py0) = layout._render_slot_patch(slot, info, convention="edge", a=-0.5)
    ph, pw = patch.shape[0], patch.shape[1]
    g = page[py0 : py0 + ph, px0 : px0 + pw, :3]
    rep = probe[py0 : py0 + ph, px0 : px0 + pw, :3]
    report("probe vs golden", rep, g)
    report("ours vs probe", patch, rep)


if __name__ == "__main__":
    main()
