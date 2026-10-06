"""CLI layout 子命令：退出码、日志落盘、页面输出。"""

import numpy as np
from PIL import Image

import helpers
from koutu.cli.main import main as cli_main


def _mini_template(path):
    img = np.full((800, 800, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:800, 0:800]
    d = np.sqrt((xx - 400) ** 2 + (yy - 400) ** 2)
    img[d <= 310] = 128
    Image.fromarray(img, "RGB").save(str(path), "PNG")


def test_cli_layout_success(tmp_path):
    demo = tmp_path / "demo.png"
    _mini_template(demo)
    src = tmp_path / "底图"
    src.mkdir()
    helpers.make_badge_image(src, "1.png", size=400, cx=200, cy=200, r=150)
    dst = tmp_path / "已排版"

    code = cli_main(
        ["layout", "--demo", str(demo), "--src", str(src), "--dst", str(dst)],
        log_dir=tmp_path,
    )
    assert code == 0
    assert (dst / "第1页.png").is_file()
    text = (tmp_path / "排版日志.txt").read_text(encoding="utf-8-sig")
    assert "共 1 页(每页 1 个槽位)" in text
    assert "p1 slot# 1" in text


def test_cli_layout_missing_demo_exit1(tmp_path):
    src = tmp_path / "底图"
    src.mkdir()
    code = cli_main(
        ["layout", "--demo", str(tmp_path / "none.png"), "--src", str(src), "--dst", str(tmp_path / "out")],
        log_dir=tmp_path,
    )
    assert code == 1
    text = (tmp_path / "排版日志.txt").read_text(encoding="utf-8-sig")
    assert "错误: 找不到模板文件" in text


def test_cli_layout_anchors_switch(tmp_path):
    """--anchors/--no-anchors：默认开启；--no-anchors 关闭（日志可辨）。"""
    demo = tmp_path / "demo.png"
    _mini_template(demo)
    src = tmp_path / "底图"
    src.mkdir()
    helpers.make_badge_image(src, "1.png", size=400, cx=200, cy=200, r=150)
    dst = tmp_path / "已排版"

    code = cli_main(
        ["layout", "--no-anchors", "--demo", str(demo), "--src", str(src), "--dst", str(dst)],
        log_dir=tmp_path,
    )
    assert code == 0
    text = (tmp_path / "排版日志.txt").read_text(encoding="utf-8-sig")
    assert "定位点: 已关闭" in text
    assert (dst / "第1页.png").is_file()

    code2 = cli_main(
        ["layout", "--demo", str(demo), "--src", str(src), "--dst", str(dst)],
        log_dir=tmp_path,
    )
    assert code2 == 0
    text2 = (tmp_path / "排版日志.txt").read_text(encoding="utf-8-sig")
    assert "定位点: 已开启（样式：黑三角；共绘制 1 处：每页 1 处 × 1 页）" in text2  # 小模板无标记也统一绘制


def test_cli_layout_custom_dst_no_clean(tmp_path):
    """CLI 自定义 --dst：只写不删 + 日志计数（flexible-io B 组「两入口同规则」）。"""
    demo = tmp_path / "demo.png"
    _mini_template(demo)
    src = tmp_path / "底图"
    src.mkdir()
    helpers.make_badge_image(src, "1.png", size=400, cx=200, cy=200, r=150)
    dst = tmp_path / "自定义 输出"
    dst.mkdir()
    (dst / "我的照片.png").write_bytes(b"user")
    (dst / "笔记.txt").write_text("x", encoding="utf-8")
    (dst / "第9页.png").write_bytes(b"stale")

    code = cli_main(
        ["layout", "--demo", str(demo), "--src", str(src), "--dst", str(dst)],
        log_dir=tmp_path,
    )
    assert code == 0
    assert (dst / "我的照片.png").is_file()
    assert (dst / "笔记.txt").is_file()
    assert (dst / "第9页.png").is_file()
    assert (dst / "第1页.png").is_file()
    text = (tmp_path / "排版日志.txt").read_text(encoding="utf-8-sig")
    assert "同名覆盖" in text and "不清理" in text


def test_cli_layout_default_dst_cleans(tmp_path, monkeypatch):
    """CLI 指向默认「已排版」（程序根）：清空语义回归（flexible-io B 组）。"""
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    demo = tmp_path / "排版demo.png"
    _mini_template(demo)
    src = tmp_path / "底图"
    src.mkdir()
    helpers.make_badge_image(src, "1.png", size=400, cx=200, cy=200, r=150)
    dst = tmp_path / "已排版"
    dst.mkdir()
    (dst / "我的照片.png").write_bytes(b"user")  # 默认目录：全部旧 *.png 清空（与 v1 一致）

    code = cli_main(["layout"], log_dir=tmp_path)
    assert code == 0
    assert not (dst / "我的照片.png").exists()
    assert (dst / "第1页.png").is_file()
    text = (tmp_path / "排版日志.txt").read_text(encoding="utf-8-sig")
    assert "将清空旧 *.png 1 张（默认输出目录）" in text
