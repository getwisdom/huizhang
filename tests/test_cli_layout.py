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
