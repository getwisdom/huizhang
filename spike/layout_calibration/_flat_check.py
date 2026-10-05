"""平坦场增益检查（开发用）。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")


def load_gray(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 0].astype(np.float64)


def main() -> None:
    for tag, scale in (("flat_s10", 10.0), ("flat_s2", 2.0)):
        p = TEMP / f"{tag}.png"
        if not p.is_file():
            print(f"[{tag}] missing")
            continue
        img = load_gray(p)
        row = img[img.shape[0] // 2]
        # 避开两端 3 个像素（边界夹取影响）
        mid = row[30:-30]
        uniq = np.unique(mid)
        print(f"[{tag}] scale={scale}  中间像素 min={mid.min()} max={mid.max()} mean={mid.mean():.3f}  唯一值={uniq[:10]}{'...' if len(uniq) > 10 else ''}")
        # 逐相位：px mod scale
        step = int(round(scale))
        for ph in range(step):
            vals = row[100 : 100 + step * 8 : step]
            print(f"   相位 {ph}: 均值={vals.mean():.3f}")


if __name__ == "__main__":
    main()
