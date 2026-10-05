"""右下角浅灰区诊断（开发用）：查源图对应区域的 alpha/RGB，与三方向量对照。"""

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
    src = info.image
    print("src size:", src.shape, "bbox:", info.min_x, info.min_y, info.max_x, info.max_y)

    # 源图右下角区域（x 380..414, y 300..414）的 alpha 统计
    box = src[300:415, 380:415]
    al = box[..., 3]
    print("源码区域 alpha: max=", int(al.max()), " >0 count=", int((al > 0).sum()), " >8 count=", int((al > 8).sum()))
    ys, xs = np.nonzero(al > 0)
    if len(xs):
        print("  alpha>0 的 x 范围:", int(xs.min()) + 380, "..", int(xs.max()) + 380,
              " y 范围:", int(ys.min()) + 300, "..", int(ys.max()) + 300)
        for k in range(0, min(8, len(xs))):
            x, y = int(xs[k]) + 380, int(ys[k]) + 300
            print(f"  src({x},{y}) rgba={src[y, x].tolist()}")
    # 更宽的 alpha 轮廓：从中心列向右扫
    row = 350
    prof = [(x, int(src[row, x, 3])) for x in range(360, 416, 5)]
    print(f"src row {row} alpha x=360..415:", prof)

    # 三方：区域行 y=700、列 770..835 的值
    patch, (px0, py0) = layout._render_slot_patch(slot, info, convention="edge", a=-0.5)
    print("region:", px0, py0, patch.shape)
    for ry in (700, 780, 830):
        print(f"region row {ry}:")
        for rx in (770, 790, 810, 825, 830, 833):
            gp = page[py0 + ry, px0 + rx, :3].tolist()
            rp = probe[py0 + ry, px0 + rx, :3].tolist()
            op = patch[ry, rx, :3].tolist()
            print(f"  rx={rx}: golden={gp} probe={rp} ours={op}")


if __name__ == "__main__":
    main()
