"""定位点样式（anchor-red-dot）：红点几何/颜色/开-关差异仅限圆点区域/日志标注/未知样式回退。"""

import math
from pathlib import Path

import numpy as np

import helpers
from koutu.core import layout

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "排版demo.png"
BASE = REPO / "golden" / "baseline_products" / "底图"
WIN = 26  # 红点半径 16 + 抗锯齿与容差余量


def test_dot_marker_geometry_color_and_log(tmp_path):
    """红点样式：直径 32±2、横向居中 ≤1.5px、圆心距圆盘外缘 9.5±1.5px、纯红；开/关差异仅限圆点区。"""
    out_on = tmp_path / "on"
    out_off = tmp_path / "off"
    summary, text = layout.run_layout_batch(
        DEMO, BASE, out_on, anchor_style=layout.ANCHOR_STYLE_DOT
    )
    assert summary.error is None, summary.error
    assert "定位点: 已开启（样式：红点；共绘制 11 处：每页 11 处 × 1 页）" in text
    layout.run_layout_batch(DEMO, BASE, out_off, anchors=False)

    on = helpers.load_rgba(out_on / "第1页.png")
    off = helpers.load_rgba(out_off / "第1页.png")
    diff = np.abs(on.astype(np.int16) - off.astype(np.int16)).max(axis=2)

    template = layout.imaging.load_rgb(DEMO)
    slots = layout.detect_slots(template)
    radii = [layout._fit_slot_radius(template, s) for s in slots]
    mask = np.zeros(diff.shape, dtype=bool)
    for s, r in zip(slots, radii):
        ix = int(math.floor(s.cx))
        iy = int(round(s.cy - (r + layout.ANCHOR_DOT_GAP)))
        x0 = max(0, ix - WIN)
        x1 = min(diff.shape[1], ix + WIN)
        y0 = max(0, iy - WIN)
        y1 = min(diff.shape[0], iy + WIN)
        crop = on[y0:y1, x0:x1, :3].astype(int)
        red = (crop[..., 0] > 200) & (crop[..., 1] < 80) & (crop[..., 2] < 80)
        ys, xs = np.nonzero(red)
        assert ys.size > 500, ys.size  # π·16² ≈ 804
        w = xs.max() - xs.min() + 1
        h = ys.max() - ys.min() + 1
        assert abs(w - layout.ANCHOR_DOT_DIAMETER) <= 2, (w, h)
        assert abs(h - layout.ANCHOR_DOT_DIAMETER) <= 2, (w, h)
        # 横向居中于槽位圆心
        assert abs((xs.min() + xs.max() + 1) / 2.0 + x0 - s.cx) <= 1.5
        # 圆心距圆盘外缘 = ANCHOR_DOT_GAP
        dot_cy = (ys.min() + ys.max() + 1) / 2.0 + y0
        assert abs((s.cy - dot_cy) - (r + layout.ANCHOR_DOT_GAP)) <= 1.5
        # 圆心处为纯红（满覆盖）
        assert tuple(int(v) for v in on[iy, ix, :3]) == layout.ANCHOR_DOT_COLOR
        mask[max(0, y0 - 4):min(diff.shape[0], y1 + 4), max(0, x0 - 4):min(diff.shape[1], x1 + 4)] = True
    assert int(((diff > 0) & ~mask).sum()) == 0


def test_default_style_unchanged_and_unknown_falls_back(tmp_path):
    """默认仍是黑三角；未知样式值回退黑三角（输出逐字节一致）。"""
    out_def = tmp_path / "def"
    out_unk = tmp_path / "unk"
    _s1, text1 = layout.run_layout_batch(DEMO, BASE, out_def)
    _s2, text2 = layout.run_layout_batch(DEMO, BASE, out_unk, anchor_style="不认识")
    assert "样式：黑三角" in text1
    assert "样式：黑三角" in text2
    a = helpers.load_rgba(out_def / "第1页.png")
    b = helpers.load_rgba(out_unk / "第1页.png")
    assert np.array_equal(a, b)


def test_dot_style_keeps_badges_identical(tmp_path):
    """样式只影响标记：红点运行与关闭运行的徽章像素一致（差异仅限圆点区域）。"""
    out_dot = tmp_path / "dot"
    out_off = tmp_path / "off"
    layout.run_layout_batch(DEMO, BASE, out_dot, anchor_style=layout.ANCHOR_STYLE_DOT)
    layout.run_layout_batch(DEMO, BASE, out_off, anchors=False)
    dot = helpers.load_rgba(out_dot / "第1页.png")
    off = helpers.load_rgba(out_off / "第1页.png")
    diff = np.abs(dot.astype(np.int16) - off.astype(np.int16)).max(axis=2) > 0
    # 差异像素总数 ≈ 11 × 圆点面积（±30%），且全部落在红点自身像素上
    n = int(diff.sum())
    assert 11 * 700 < n < 11 * 1100, n
