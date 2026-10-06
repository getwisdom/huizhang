"""排版圆心实测（layout-center）：图案模板校正 / 干净模板不变 / 回退路径 / 徽章与定位点同源。"""

import math
from pathlib import Path

import numpy as np
from PIL import Image

import helpers
from koutu.core import layout

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "排版demo.png"
BASE = REPO / "golden" / "baseline_products" / "底图"


def _save(img: np.ndarray, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGB").save(str(path), "PNG")
    return path


def _badge(path: Path, *, size=800, cx=400, cy=400, r=200, color=(255, 0, 0)) -> Path:
    """透明背景 + 实色圆：在输出页上可用实色质心量出徽章实际落点。"""
    img = np.zeros((size, size, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    m = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) <= r
    img[m, :3] = color
    img[m, 3] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(str(path), "PNG")
    return path


def _patterned_template(path: Path) -> tuple[Path, float, float, float]:
    """白底 + 灰色圆盘（圆心 600,600 半径 300）+ 左侧粘连花瓣条。

    花瓣条与圆盘连通，使 `detect_slots` 的包围盒左扩 —— 复刻现场「图案干扰抬高/推偏检测圆心」的机制。
    """
    size = 1200
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    img[np.sqrt((xx - 600) ** 2 + (yy - 600) ** 2) <= 300] = 150
    img[590:611, 240:301] = 150  # 与圆盘左缘相接的花瓣条
    return _save(img, path), 600.0, 600.0, 300.0


def test_clean_template_keeps_detected_center():
    """入库旧模板：实测圆心与检测圆心只差 0.1px 量级 ⇒ 沿用检测圆心（既有输出逐像素不变）。"""
    template = layout.imaging.load_rgb(DEMO)
    slots = layout.detect_slots(template)
    assert len(slots) == 11
    for s in slots:
        cx, cy = layout._measure_slot_center(template, s)
        assert (cx, cy) == (s.cx, s.cy), (s.cx, s.cy, cx, cy)


def test_measure_center_corrects_biased_seed(tmp_path):
    """图案模板：以被花瓣推偏的检测圆心为种子，实测应回到真圆心（≤1px）。"""
    demo, tx, ty, _tr = _patterned_template(tmp_path / "demo.png")
    template = layout.imaging.load_rgb(demo)
    slots = layout.detect_slots(template)
    assert len(slots) == 1
    det = slots[0]
    assert det.cx < tx - 5, det  # 前提：检测圆心确实被花瓣推偏（现场同机制）
    cx, cy = layout._measure_slot_center(template, det)
    assert abs(cx - tx) <= 1.0, (cx, tx)
    assert abs(cy - ty) <= 1.0, (cy, ty)

    # 亚像素偏差：不改动（沿用检测圆心）
    near = layout.Slot(cx=tx + 0.4, cy=ty - 0.3, r=det.r)
    assert layout._measure_slot_center(template, near) == (near.cx, near.cy)


def test_measure_center_fallback_paths(tmp_path):
    """无边界 / 边界点不足 / 拟合半径异常 ⇒ 回退检测圆心，不报错。"""
    blank = layout.imaging.load_rgb(_save(np.full((1200, 1200, 3), 255, dtype=np.uint8), tmp_path / "blank.png"))
    seed = layout.Slot(cx=600.0, cy=610.0, r=310.0)
    assert layout._measure_slot_center(blank, seed) == (seed.cx, seed.cy)

    few = np.full((1200, 1200, 3), 255, dtype=np.uint8)
    few[200:230, 200:230] = 0  # 远离种子的孤立小块：命中角数不足
    tpl_few = layout.imaging.load_rgb(_save(few, tmp_path / "few.png"))
    assert layout._measure_slot_center(tpl_few, seed) == (seed.cx, seed.cy)

    small = np.full((1200, 1200, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:1200, 0:1200]
    small[np.sqrt((xx - 600) ** 2 + (yy - 610) ** 2) <= 60] = 120  # 半径 60 < MIN_SLOT_RADIUS
    tpl_small = layout.imaging.load_rgb(_save(small, tmp_path / "small.png"))
    assert layout._measure_slot_center(tpl_small, seed) == (seed.cx, seed.cy)


def test_batch_badge_and_anchor_use_measured_center(tmp_path):
    """整批：徽章与定位点都按实测圆心落位；日志出现「圆盘实测」行与实际使用的圆心。"""
    demo, tx, ty, _tr = _patterned_template(tmp_path / "demo.png")
    base = tmp_path / "底图"
    _badge(base / "1.png")
    slots = layout.detect_slots(layout.imaging.load_rgb(demo))
    out_on = tmp_path / "on"
    summary, text = layout.run_layout_batch(demo, base, out_on)
    assert summary.error is None, summary.error
    assert "圆盘实测: 1 个槽位" in text

    page = helpers.load_rgba(out_on / "第1页.png")
    red = (page[..., 0] > 200) & (page[..., 1] < 60) & (page[..., 2] < 60)
    ys, xs = np.nonzero(red)
    assert ys.size > 1000
    cx = (xs.min() + xs.max() + 1) / 2.0
    cy = (ys.min() + ys.max() + 1) / 2.0
    assert abs(cx - tx) <= 1.5, (cx, tx)
    assert abs(cy - ty) <= 1.5, (cy, ty)

    alloc = helpers.parse_layout_alloc(text)
    assert len(alloc) == 1
    assert abs(alloc[0]["x"] - tx) <= 1 and abs(alloc[0]["y"] - ty) <= 1, alloc
    # 定位点与徽章同源：开/关差异区域的横向中点 = 实测圆心 x（而非被推偏的检测圆心）
    out_off = tmp_path / "off"
    layout.run_layout_batch(demo, base, out_off, anchors=False)
    off = helpers.load_rgba(out_off / "第1页.png")
    diff = np.abs(page.astype(np.int16) - off.astype(np.int16)).max(axis=2) > 0
    ys2, xs2 = np.nonzero(diff)
    assert ys2.size > 30
    mid_x = (xs2.min() + xs2.max() + 1) / 2.0
    assert abs(mid_x - tx) <= 2.0, (mid_x, tx)
    # 纵向：定位点顶端紧贴实测圆外缘（顶端距外缘 8.5px、黑边 6.5px ⇒ 可见顶端约 -5px）
    r_draw = layout._fit_slot_radius(layout.imaging.load_rgb(demo), slots[0])
    assert abs(ys2.min() - (ty - r_draw + 5.0)) <= 3.0, (ys2.min(), ty, r_draw)
