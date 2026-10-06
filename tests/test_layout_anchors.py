"""排版定位点（layout-anchors）：窗口搬运逐像素一致 / 关闭不搬运 / 降级 / 叠法。"""

import math
from pathlib import Path

import numpy as np
from PIL import Image

import helpers
from koutu.core import layout

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "排版demo.png"
BASE = REPO / "golden" / "baseline_products" / "底图"


def _window(slot):
    cx0 = math.floor(slot.cx + 0.5)
    cy0 = math.floor(slot.cy + 0.5)
    return cx0 - 20, cy0 - 406, 40, 19


def _mini_template(tmp_path, name="demo.png"):
    img = np.full((800, 800, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:800, 0:800]
    d = np.sqrt((xx - 400) ** 2 + (yy - 400) ** 2)
    img[d <= 310] = 128
    p = tmp_path / name
    Image.fromarray(img, "RGB").save(str(p), "PNG")
    return p


def test_anchors_on_windows_equal_template(tmp_path):
    """默认开启（含底）：每个槽位（含空槽）窗口与模板同区域逐像素相等 + 数量行。"""
    out = tmp_path / "已排版"
    summary, text = layout.run_layout_batch(DEMO, BASE, out)
    assert summary.error is None
    template = layout.imaging.load_rgb(DEMO)
    page = helpers.load_rgba(out / "第1页.png")
    slots = layout.detect_slots(template)
    assert len(slots) == 11
    for s in slots:  # 末 4 个槽位留白（空槽也画）
        x0, y0, w, h = _window(s)
        assert np.array_equal(
            page[y0:y0 + h, x0:x0 + w, :3], template[y0:y0 + h, x0:x0 + w, :3]
        )
    assert "定位点: 已开启（共绘制 11 处：每页 11 处 × 1 页）" in text


def test_anchors_off_no_stamp(tmp_path):
    """关闭：不搬运任何补丁（空槽窗口纯白），日志含「已关闭」。"""
    out = tmp_path / "已排版"
    summary, text = layout.run_layout_batch(DEMO, BASE, out, anchors=False)
    assert summary.error is None
    template = layout.imaging.load_rgb(DEMO)
    page = helpers.load_rgba(out / "第1页.png")
    slots = layout.detect_slots(template)
    x0, y0, w, h = _window(slots[7])
    assert (page[y0:y0 + h, x0:x0 + w, :3] == 255).all()
    assert "定位点: 已关闭" in text


def test_anchors_degrade_on_template_without_mark(tmp_path):
    """换模板无标记：安全降级（不报错、逐像素不变），日志一句。"""
    demo = _mini_template(tmp_path)
    base = tmp_path / "底图"
    base.mkdir()
    helpers.make_badge_image(base, "1.png", size=400, cx=200, cy=200, r=150)

    out_on = tmp_path / "已排版_on"
    summary, text = layout.run_layout_batch(demo, base, out_on)
    assert summary.error is None
    assert "定位点: 已开启（模板上未检测到标记，已跳过）" in text

    out_off = tmp_path / "已排版_off"
    layout.run_layout_batch(demo, base, out_off, anchors=False)
    on_page = helpers.load_rgba(out_on / "第1页.png")
    off_page = helpers.load_rgba(out_off / "第1页.png")
    assert np.array_equal(on_page, off_page)  # 降级不改变任何像素


def test_anchor_strip_only_dark_strokes(tmp_path):
    """去底叠法（样张对照用）：底色不搬运（角落保持白）、暗笔画可见。"""
    out = tmp_path / "已排版"
    summary, text = layout.run_layout_batch(DEMO, BASE, out, anchor_mode="去底")
    assert summary.error is None
    template = layout.imaging.load_rgb(DEMO)
    page = helpers.load_rgba(out / "第1页.png")
    slots = layout.detect_slots(template)
    x0, y0, w, h = _window(slots[7])
    win = page[y0:y0 + h, x0:x0 + w, :3]
    assert (win[0, 0] == 255).all()  # 左上角：底色未被搬运
    assert int(win.min()) < 100  # 三角笔画仍在

    out2 = tmp_path / "已排版2"
    layout.run_layout_batch(DEMO, BASE, out2)
    win2 = helpers.load_rgba(out2 / "第1页.png")[y0:y0 + h, x0:x0 + w, :3]
    assert not (win2[0, 0] == 255).all()  # 含底叠法带浅色底（角像素非纯白）
