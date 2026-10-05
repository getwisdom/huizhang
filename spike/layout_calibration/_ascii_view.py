"""ASCII 内容分布视图（开发用）：src / golden / probe 三者对照。"""

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


def ascii_map(arr2d: np.ndarray, step: int, chars=" .:-=+*#@") -> None:
    h, w = arr2d.shape
    for y in range(0, h, step):
        row = []
        for x in range(0, w, step):
            v = arr2d[y : y + step, x : x + step]
            row.append(chars[min(len(chars) - 1, int(v.mean() / 256 * len(chars)))])
        print("".join(row))


def main() -> None:
    page = load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
    probe = load_rgba(TEMP / "probe_slot1.png")
    template = imaging.load_rgb(REPO / "排版demo.png")
    slots = layout.detect_slots(template)
    infos, _ = layout.load_base_infos(REPO / "golden" / "baseline_products" / "底图")
    src = infos[0].image

    print("=== src 1.png 全图 alpha 视图（4px 采样） ===")
    ascii_map(src[..., 3], 4)
    print("=== src 1.png 全图 luma 视图（4px 采样） ===")
    luma = src[..., :3].mean(axis=2)
    ascii_map(np.where(src[..., 3] > 8, luma, 0), 4)

    # golden slot1 区域（页坐标 30..930，8px）
    reg = page[30:930, 30:930, :3]
    nonwhite = (255 - reg.mean(axis=2)).astype(np.float64)
    print("=== golden 页 slot1 附近（30..930, 8px 采样；非白强度） ===")
    ascii_map(nonwhite * 3, 8)

    reg2 = probe[30:930, 30:930, :3]
    nonwhite2 = (255 - reg2.mean(axis=2)).astype(np.float64)
    print("=== probe slot1 附近（同范围，8px） ===")
    ascii_map(nonwhite2 * 3, 8)


if __name__ == "__main__":
    main()
