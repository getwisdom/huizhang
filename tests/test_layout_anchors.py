"""排版定位点（layout-fit）：自绘统一小三角 / 关闭不画 / 与模板无关 / 差异仅限标记区。"""

import math
from pathlib import Path

import numpy as np
from PIL import Image

import helpers
from koutu.core import layout

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "排版demo.png"
BASE = REPO / "golden" / "baseline_products" / "底图"


def _marker_region(slot, r):
    """定位点影响区域（含抗锯齿余量；返回 x0, y0, x1, y1，半开区间）。"""
    cx = int(math.floor(slot.cx))
    y0 = int(math.floor(slot.cy - r + 3 + 0.5))
    return cx - 17, y0, cx + 18, y0 + 29


def test_anchors_uniform_markers_and_log(tmp_path):
    """默认开启：每槽位标记存在、各槽位逐像素一致；开/关差异仅限标记区域；数量行。"""
    out_on = tmp_path / "已排版_on"
    summary, text = layout.run_layout_batch(DEMO, BASE, out_on)
    assert summary.error is None
    out_off = tmp_path / "已排版_off"
    layout.run_layout_batch(DEMO, BASE, out_off, anchors=False)
    on = helpers.load_rgba(out_on / "第1页.png")
    off = helpers.load_rgba(out_off / "第1页.png")
    diff = np.abs(on.astype(np.int16) - off.astype(np.int16)).max(axis=2)

    template = layout.imaging.load_rgb(DEMO)
    slots = layout.detect_slots(template)
    assert len(slots) == 11
    radii = [layout._fit_slot_radius(template, s) for s in slots]
    crops = []
    mask = np.zeros(diff.shape, dtype=bool)
    for s, r in zip(slots, radii):
        x0, y0, x1, y1 = _marker_region(s, r)
        crop = diff[y0:y1, x0:x1]
        assert (crop > 0).sum() > 30  # 标记存在（含空槽）
        crops.append(crop)
        mask[y0:y1, x0:x1] = True
    # 统一：空槽（白底）上的标记差异图逐像素一致（索引 7..10 为留白槽）
    for k in (8, 9, 10):
        assert np.array_equal(crops[7], crops[k])
    # 开/关差异仅限标记区域
    assert int(((diff > 0) & ~mask).sum()) == 0
    assert "定位点: 已开启（共绘制 11 处：每页 11 处 × 1 页）" in text


def test_anchors_off_no_marker(tmp_path):
    out = tmp_path / "已排版"
    summary, text = layout.run_layout_batch(DEMO, BASE, out, anchors=False)
    assert summary.error is None
    assert "定位点: 已关闭" in text
    assert "已开启" not in text


def test_marker_geometry_hugs_circle(tmp_path):
    """几何：顶端距圆外缘 ~8.5px、底端 ~25.5px、底半宽 ~12px（含抗锯齿余量）。"""
    out_on = tmp_path / "on"
    out_off = tmp_path / "off"
    layout.run_layout_batch(DEMO, BASE, out_on)
    layout.run_layout_batch(DEMO, BASE, out_off, anchors=False)
    on = helpers.load_rgba(out_on / "第1页.png")
    off = helpers.load_rgba(out_off / "第1页.png")
    diff = np.abs(on.astype(np.int16) - off.astype(np.int16)).max(axis=2) > 0

    template = layout.imaging.load_rgb(DEMO)
    s = layout.detect_slots(template)[0]
    r = layout._fit_slot_radius(template, s)
    x0 = int(math.floor(s.cx)) - 40
    y0 = int(round(s.cy - r - 20))
    crop = diff[y0:y0 + 80, x0:x0 + 80]
    ys, xs = np.nonzero(crop)
    assert ys.size > 0
    edge = s.cy - r
    top = ys.min() + y0 - edge
    bot = ys.max() + y0 - edge
    halfw = (xs.max() - xs.min() + 1) / 2.0
    assert 3.5 <= top <= 7.0, top
    assert 26.0 <= bot <= 31.0, bot
    assert 14.0 <= halfw <= 18.5, halfw


def test_markers_drawn_on_template_without_mark(tmp_path):
    """小模板（无任何标记）：仍统一绘制、不报错（自绘方案与模板无关）。"""
    img = np.full((800, 800, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:800, 0:800]
    d = np.sqrt((xx - 400) ** 2 + (yy - 400) ** 2)
    img[d <= 310] = 128
    demo = tmp_path / "demo.png"
    Image.fromarray(img, "RGB").save(str(demo), "PNG")
    base = tmp_path / "底图"
    base.mkdir()
    helpers.make_badge_image(base, "1.png", size=400, cx=200, cy=200, r=150)

    out_on = tmp_path / "on"
    summary, text = layout.run_layout_batch(demo, base, out_on)
    assert summary.error is None
    assert "定位点: 已开启（共绘制 1 处：每页 1 处 × 1 页）" in text
    out_off = tmp_path / "off"
    layout.run_layout_batch(demo, base, out_off, anchors=False)
    on = helpers.load_rgba(out_on / "第1页.png")
    off = helpers.load_rgba(out_off / "第1页.png")
    diff = np.abs(on.astype(np.int16) - off.astype(np.int16)).max(axis=2)
    assert (diff[88:125, 380:420] > 0).sum() > 30  # 标记在圆顶内侧（白底上）
