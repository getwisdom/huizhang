"""空心圆环模板（outline-template）：主路径打散时自动细采样回退，识别圆环槽位。"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from koutu.core import layout

REPO = Path(__file__).resolve().parents[1]
WUTU = REPO / "无图模板.jpg"  # 使用者的空心圆环模板（未放在仓库根时跳过实跑用例）


def _ring_template(path: Path, *, size=1200, cx=600, cy=600, r=310, thickness=3) -> Path:
    """白底 + 细黑圆环（圆内空白、无图案）——复刻「圆内无图、只有圆环轮廓」的模板。"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    img[(d <= r) & (d >= r - thickness)] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGB").save(str(path), "PNG")
    return path


def test_ring_template_falls_back_to_fine_step(tmp_path):
    """细圆环模板：主路径（步长 4）打散 → 回退（步长 2）识别出 1 个槽位，圆心/半径正确。"""
    template = layout.imaging.load_rgb(_ring_template(tmp_path / "ring.png"))
    slots, step = layout.detect_slots_ex(template)
    assert step == layout.DETECT_FALLBACK_STEP, step
    assert len(slots) == 1, slots
    s = slots[0]
    assert abs(s.cx - 600) <= 2, s.cx
    assert abs(s.cy - 600) <= 2, s.cy
    assert abs(s.r - 310) <= 4, s.r
    # 包装函数与显式调用一致
    assert layout.detect_slots(template) == slots


def test_solid_disc_uses_primary_step(tmp_path):
    """实心圆盘模板：主路径即可识别（回退不触发），步长仍为 4。"""
    img = np.full((1200, 1200, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:1200, 0:1200]
    img[np.sqrt((xx - 600) ** 2 + (yy - 600) ** 2) <= 310] = 128
    demo = tmp_path / "disc.png"
    Image.fromarray(img, "RGB").save(str(demo), "PNG")
    slots, step = layout.detect_slots_ex(layout.imaging.load_rgb(demo))
    assert step == layout.STEP
    assert len(slots) == 1


@pytest.mark.skipif(not WUTU.is_file(), reason="仓库根没有 无图模板.jpg")
def test_wutu_template_eleven_slots_and_grid():
    """真身空心圆环模板：回退识别 11 槽位；实测圆径 412、行距 442.6 等距。"""
    template = layout.imaging.load_rgb(WUTU)
    slots, step = layout.detect_slots_ex(template)
    assert step == layout.DETECT_FALLBACK_STEP, step
    assert len(slots) == 11, len(slots)

    radii = [layout._fit_slot_radius(template, s) for s in slots]
    assert all(abs(r - 412.0) <= 2.0 for r in radii), radii

    centers = [layout._measure_slot_center(template, s) for s in slots]
    rows: list[list[float]] = []
    for _, cy in sorted(centers, key=lambda c: c[1]):
        if rows and abs(cy - rows[-1][-1]) <= 5:
            rows[-1].append(cy)
        else:
            rows.append([cy])
    means = [sum(r) / len(r) for r in rows]
    assert len(means) == 7, means
    gaps = [b - a for a, b in zip(means, means[1:])]
    assert all(abs(g - 442.6) <= 1.0 for g in gaps), gaps
