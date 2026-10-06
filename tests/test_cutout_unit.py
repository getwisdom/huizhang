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


def test_cutout_cancel_status_line(tmp_path):
    """取消：日志含「已取消：成功 X 张，失败 Y 张」（flexible-io D6）。"""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    for i in range(1, 4):
        helpers.make_badge_image(src_dir, f"{i}.png")
    calls = {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] > 1  # 第 1 张后取消

    summary, text = cutout.run_cutout_batch(
        src_dir, tmp_path / "dst", log_path=tmp_path / "log.txt", cancel=cancel
    )
    assert summary.cancelled is True
    assert summary.ok == 1
    assert "已取消：成功 1 张，失败 0 张" in text
    assert "全部完成" not in text
    assert (tmp_path / "dst" / "1.png").is_file()
    assert not (tmp_path / "dst" / "3.png").exists()
    content = (tmp_path / "log.txt").read_text(encoding="utf-8-sig")
    assert "已取消：成功 1 张，失败 0 张" in content


def test_cutout_run_precheck_line(tmp_path):
    """运行前计数提示：输入张数与同名覆盖数（flexible-io D4）。"""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    helpers.make_badge_image(src_dir, "a.png")
    helpers.make_badge_image(src_dir, "b.png")
    dst = tmp_path / "dst"
    dst.mkdir()
    helpers.make_badge_image(dst, "a.png")  # 同名产物预置 → 应计 1 个

    summary, text = cutout.run_cutout_batch(src_dir, dst)
    assert summary.ok == 2
    assert "运行前: 输入 2 张；同名覆盖 1 个；抠图不清理输出目录" in text


def test_cutout_unexpected_error_writes_log(tmp_path):
    """未预期异常：日志兜底落盘并带中文「错误:」行与完整输入路径（flexible-io D6）。"""
    import pytest

    bad_src = tmp_path / "其实是个文件"
    bad_src.write_text("not a dir", encoding="utf-8")
    log = tmp_path / "log.txt"
    with pytest.raises(OSError):
        cutout.run_cutout_batch(bad_src, tmp_path / "dst", log_path=log)
    content = log.read_text(encoding="utf-8-sig")
    assert "错误: 未预期错误" in content
    assert str(bad_src) in content  # 兜底时补记完整输入路径
