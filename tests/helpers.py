"""测试辅助：像素对照（口径与 golden/scripts/pixel-diff.ps1 一致）与合成样张。"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgba(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def compare_rgba(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape != b.shape:
        return {"size_equal": False, "shape_a": a.shape, "shape_b": b.shape}
    al_a = a[..., 3].astype(np.int16)
    al_b = b[..., 3].astype(np.int16)
    diff = np.abs(al_a - al_b)
    both = (al_a > 8) & (al_b > 8)
    rgb = np.abs(a[..., :3].astype(np.int16) - b[..., :3].astype(np.int16)).max(axis=2)
    total = int(a.shape[0] * a.shape[1])
    return {
        "size_equal": True,
        "total": total,
        "opaque_a": int((al_a > 0).sum()),
        "opaque_b": int((al_b > 0).sum()),
        "alpha_gt8": int((diff > 8).sum()),
        "alpha_gt8_ratio": float((diff > 8).sum()) / total,
        "max_alpha_diff": int(diff.max()),
        "rgb_gt8": int(((rgb > 8) & both).sum()),
        "rgb_gt8_ratio": float(((rgb > 8) & both).sum()) / total,
    }


CUTOUT_LOG_RE = re.compile(
    r"\[完成\]\s+(.+?) -> (\S+)\s+\(OK (\d+)x(\d+) 圆心\((-?\d+),(-?\d+)\) 半径(\d+)\)"
)


def parse_cutout_log(text: str) -> dict:
    out = {}
    for m in CUTOUT_LOG_RE.finditer(text):
        out[m.group(1)] = {
            "out": m.group(2),
            "w": int(m.group(3)),
            "h": int(m.group(4)),
            "cx": int(m.group(5)),
            "cy": int(m.group(6)),
            "r": int(m.group(7)),
        }
    return out


LAYOUT_ALLOC_RE = re.compile(
    r"p(\d+) slot#\s*(\d+) \((\d+),(\d+)\) <- (.+?)\s*$", re.MULTILINE
)


def parse_layout_alloc(text: str) -> list:
    return [
        {
            "page": int(m.group(1)),
            "slot": int(m.group(2)),
            "x": int(m.group(3)),
            "y": int(m.group(4)),
            "file": m.group(5).strip(),
        }
        for m in LAYOUT_ALLOC_RE.finditer(text)
    ]


def make_badge_image(directory, name="badge.png", size=800, cx=400, cy=400, r=200):
    """合成一张「背景 + 圆形徽章 + 圆内浅色纹样」的样张，用于单元/CLI 测试。"""
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[..., :3] = 30
    img[..., 3] = 255
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    img[d <= r, :3] = 128
    img[(d <= r - 30) & ((xx + yy) % 80 < 30), :3] = 245
    p = Path(directory) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(str(p), "PNG")
    return p


def pump_until(qapp, cond, timeout=30.0):
    """在 offscreen 测试里驱动事件循环，直到条件满足或超时；返回最终条件值。"""
    import time

    deadline = time.time() + timeout
    while not cond() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    qapp.processEvents()
    return cond()
