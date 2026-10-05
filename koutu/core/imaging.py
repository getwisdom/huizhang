"""像素读写工具（numpy/PIL）。

约定：
- 图像读写统一走本模块；
- 保存失败重试并抛错（参照 docs/环境验证.md §4 对首跑瞬态失败的建议，不静默）。
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgb(path) -> np.ndarray:
    """读为 RGB uint8 数组（与旧实现「非 3/4 通道先转 24bpp」语义等价）。"""
    with Image.open(path) as im:
        if im.mode != "RGB":
            im = im.convert("RGB")
        return np.asarray(im, dtype=np.uint8)


def load_rgba(path) -> np.ndarray:
    """读为 RGBA uint8 数组（无 alpha 的图 alpha 补 255）。"""
    with Image.open(path) as im:
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        return np.asarray(im, dtype=np.uint8)


def save_rgba(path, arr: np.ndarray, retries: int = 2) -> None:
    """保存 32 位 RGBA PNG；失败重试，最终失败抛 OSError。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for _ in range(retries + 1):
        try:
            Image.fromarray(arr, "RGBA").save(str(p), "PNG")
            return
        except OSError as exc:  # 首跑瞬态（见环境验证 §4）
            last = exc
            time.sleep(0.05)
    raise OSError(f"保存失败: {last}")


def resize_rgba(arr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """高质量（双三次）缩放 RGBA 数组到目标 (宽, 高)。"""
    im = Image.fromarray(arr, "RGBA").resize(
        (int(size[0]), int(size[1])), Image.Resampling.BICUBIC
    )
    return np.asarray(im, dtype=np.uint8)
