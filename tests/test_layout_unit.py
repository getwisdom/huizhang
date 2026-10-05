"""排版单元测试：槽位识别、无效模板、合成与清空旧页、空底图。"""

import shutil

import numpy as np
from PIL import Image

import helpers
from koutu.core import layout

REPO = __import__("pathlib").Path(__file__).resolve().parents[1]


def _write_template(path, data: np.ndarray) -> None:
    Image.fromarray(data, "RGB").save(str(path), "PNG")


def _mini_template(tmp_path, name="demo.png"):
    """800×800 白底 + 1 个半径 310 的灰圆（满足 ≥300 的槽位半径下限）。"""
    img = np.full((800, 800, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:800, 0:800]
    d = np.sqrt((xx - 400) ** 2 + (yy - 400) ** 2)
    img[d <= 310] = 128
    p = tmp_path / name
    _write_template(p, img)
    return p


def test_detect_slots_on_real_template():
    demo = REPO / "排版demo.png"
    if not demo.is_file():
        import pytest

        pytest.skip("缺少 排版demo.png")
    template = layout.imaging.load_rgb(demo)
    slots = layout.detect_slots(template)
    assert len(slots) == 11
    for s in slots:
        assert abs(s.r - 414.0) <= 0.01
    assert (slots[0].cx, slots[0].cy) == (474.5, 448.5)
    assert (slots[1].cx, slots[1].cy) == (2017.5, 448.5)


def test_invalid_template_raises(tmp_path):
    blank = tmp_path / "blank.png"
    _write_template(blank, np.full((600, 400, 3), 255, dtype=np.uint8))
    summary, text = layout.run_layout_batch(blank, tmp_path / "底图", tmp_path / "已排版")
    assert summary.error is not None
    assert "没有识别到圆形槽位" in summary.error
    assert "错误:" in text


def test_missing_demo_raises(tmp_path):
    summary, text = layout.run_layout_batch(
        tmp_path / "none.png", tmp_path / "底图", tmp_path / "已排版"
    )
    assert summary.error is not None
    assert "找不到模板文件" in summary.error


def test_missing_base_dir_raises(tmp_path):
    demo = _mini_template(tmp_path)
    summary, text = layout.run_layout_batch(
        demo, tmp_path / "nope", tmp_path / "已排版"
    )
    assert summary.error is not None
    assert "找不到输入文件夹" in summary.error


def test_mini_end_to_end_and_clear_old(tmp_path):
    demo = _mini_template(tmp_path)
    base = tmp_path / "底图"
    base.mkdir()
    helpers.make_badge_image(base, "1.png", size=400, cx=200, cy=200, r=150)
    helpers.make_badge_image(base, "2.png", size=400, cx=200, cy=200, r=150)
    out = tmp_path / "已排版"

    summary, text = layout.run_layout_batch(demo, base, out)
    assert summary.error is None
    assert summary.pages == 2 and summary.slots == 1 and summary.bases == 2

    page1 = helpers.load_rgba(out / "第1页.png")
    assert page1.shape == (800, 800, 4)
    assert (page1[..., 3] == 255).all()

    # 重复运行：旧页先清空（塞一个旧文件应被删除）
    stale = out / "旧页.png"
    stale.write_bytes(b"stale")
    summary2, _ = layout.run_layout_batch(demo, base, out)
    assert summary2.pages == 2
    assert not stale.exists()
    assert (out / "第1页.png").is_file() and (out / "第2页.png").is_file()


def test_skip_empty_base_and_count(tmp_path):
    demo = _mini_template(tmp_path)
    base = tmp_path / "底图"
    base.mkdir()
    helpers.make_badge_image(base, "1.png", size=400, cx=200, cy=200, r=150)
    empty = np.zeros((100, 100, 4), dtype=np.uint8)  # 全透明
    Image.fromarray(empty, "RGBA").save(str(base / "2.png"), "PNG")

    summary, text = layout.run_layout_batch(demo, base, tmp_path / "已排版")
    assert summary.error is None
    assert summary.bases == 1
    assert "跳过 2.png" in text
    assert "底图数量: 1" in text


def test_alloc_line_format(tmp_path):
    demo = _mini_template(tmp_path)
    base = tmp_path / "底图"
    base.mkdir()
    helpers.make_badge_image(base, "7.png", size=400, cx=200, cy=200, r=150)
    summary, text = layout.run_layout_batch(demo, base, tmp_path / "已排版")
    assert summary.error is None
    assert "  p1 slot# 1 (400,400) <- 7.png" in text
