"""平移假设检验（开发用）：probe vs golden / ours vs probe 在不同整体位移下的差异。"""

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


def main() -> None:
    page = load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
    probe = load_rgba(TEMP / "probe_slot1.png")
    template = imaging.load_rgb(REPO / "排版demo.png")
    slots = layout.detect_slots(template)
    infos, _ = layout.load_base_infos(REPO / "golden" / "baseline_products" / "底图")
    slot, info = slots[0], infos[0]
    patch, (px0, py0) = layout._render_slot_patch(slot, info, convention="edge", a=-0.5)
    ph, pw = patch.shape[0], patch.shape[1]
    print("region origin:", px0, py0, "size:", ph, pw)

    g = page[py0 : py0 + ph, px0 : px0 + pw, :3].astype(np.int16)

    print("\n== probe（整体平移）vs golden ==")
    results = []
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            p2 = np.roll(probe, (dy, dx), axis=(0, 1))[py0 : py0 + ph, px0 : px0 + pw, :3].astype(np.int16)
            d = np.abs(p2 - g).max(axis=2)
            results.append((int((d > 8).sum()), float(d.mean()), dx, dy))
    for r in sorted(results)[:8]:
        print(f"  gt8={r[0]:>7} mean={r[1]:.4f}  shift=({r[2]:+d},{r[3]:+d})")

    print("\n== ours（整体平移）vs golden ==")
    results = []
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            p2 = np.roll(patch, (dy, dx), axis=(0, 1)).astype(np.int16)
            d = np.abs(p2 - g).max(axis=2)
            results.append((int((d > 8).sum()), float(d.mean()), dx, dy))
    for r in sorted(results)[:8]:
        print(f"  gt8={r[0]:>7} mean={r[1]:.4f}  shift=({r[2]:+d},{r[3]:+d})")

    # 针对差异区，具体打印 golden 与 probe 的邻域值（行 y=700）
    print("\n区域行 700，x=795..835：golden / probe（RGB）")
    for rx in range(795, 836, 2):
        gv = page[py0 + 700, px0 + rx, :3].tolist()
        pv = probe[py0 + 700, px0 + rx, :3].tolist()
        print(f"  x={rx}: {gv}  {pv}")


if __name__ == "__main__":
    main()
