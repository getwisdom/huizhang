"""抠图单元测试：合成样张上的定位、圆内无空洞、失败隔离。"""

import shutil

import numpy as np

import helpers
from koutu.core import cutout
from koutu.core.imaging import load_rgba


def test_cutout_finds_circle_and_keeps_interior(tmp_path):
    src = helpers.make_badge_image(tmp_path, "badge.png")
    res = cutout.process_image(src, tmp_path / "out.png", 45.0, 4, 4)
    assert res.ok, res.error
    assert abs(res.cx - 400) <= 2 and abs(res.cy - 400) <= 2
    # 合成样张为硬边缘（真实照片是软边缘），扫描交点系统性外移 ~1–2px，容差放到 ±3
    assert abs(res.r - 200) <= 3
    out = load_rgba(tmp_path / "out.png")
    ch, cw = out.shape[0], out.shape[1]
    yy, xx = np.mgrid[0:ch, 0:cw]
    # 输出是裁剪图：把圆心换算到输出坐标（裁剪原点 = 圆心±(半径+羽化4+边距4)，含图内夹取）
    cx0 = max(0, int(res.cx - res.r - 4 - 4))
    cy0 = max(0, int(res.cy - res.r - 4 - 4))
    dd = np.sqrt((xx + 0.5 + cx0 - res.cx) ** 2 + (yy + 0.5 + cy0 - res.cy) ** 2)
    # 圆内（留 2px 余量）不允许任何透明/半透明像素
    assert (out[dd <= res.r - 2, 3] == 255).all()
    opaque = int((out[..., 3] > 0).sum())
    ratio = opaque / (np.pi * res.r * res.r)
    assert 0.98 <= ratio <= 1.08, ratio


def test_cutout_failure_isolation(tmp_path):
    good = helpers.make_badge_image(tmp_path, "good.png")
    solid_path = tmp_path / "solid.png"
    arr = np.zeros((300, 300, 4), dtype=np.uint8)
    arr[..., :3] = 77
    arr[..., 3] = 255
    from PIL import Image

    Image.fromarray(arr, "RGBA").save(str(solid_path), "PNG")

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    shutil.copy(good, src_dir / "good.png")
    shutil.copy(solid_path, src_dir / "solid.png")

    summary, text = cutout.run_cutout_batch(
        src_dir, tmp_path / "dst", log_path=tmp_path / "log.txt"
    )
    assert summary.ok == 1
    assert summary.fail == 1
    assert "[失败] solid.png" in text
    assert "全部完成：成功 1 张，失败 1 张" in text
    assert (tmp_path / "log.txt").is_file()


def test_cutout_empty_dir(tmp_path):
    src_dir = tmp_path / "empty"
    src_dir.mkdir()
    summary, text = cutout.run_cutout_batch(src_dir, tmp_path / "dst")
    assert summary.ok == 0 and summary.fail == 0
    assert "[提示] 原图文件夹里没有图片文件" in text
