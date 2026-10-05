"""CLI cutout 子命令：退出码、日志落盘与文件集合。"""

import helpers
from koutu.cli.main import main as cli_main


def test_cli_cutout_success(tmp_path):
    src = tmp_path / "input"
    src.mkdir()
    helpers.make_badge_image(src, "badge.png")
    dst = tmp_path / "out"

    code = cli_main(["cutout", "--src", str(src), "--dst", str(dst)], log_dir=tmp_path)
    assert code == 0
    log = tmp_path / "运行日志.txt"
    assert log.is_file()
    text = log.read_text(encoding="utf-8-sig")
    assert "全部完成：成功 1 张，失败 0 张" in text
    assert (dst / "badge.png").is_file()


def test_cli_cutout_failure_code(tmp_path):
    src = tmp_path / "input2"
    src.mkdir()
    (src / "broken.png").write_bytes(b"not an image")
    dst = tmp_path / "out2"

    code = cli_main(["cutout", "--src", str(src), "--dst", str(dst)], log_dir=tmp_path)
    assert code == 1
    text = (tmp_path / "运行日志.txt").read_text(encoding="utf-8-sig")
    assert "[失败] broken.png" in text


def test_cli_cutout_empty_is_success(tmp_path):
    src = tmp_path / "input3"
    src.mkdir()
    dst = tmp_path / "out3"
    code = cli_main(["cutout", "--src", str(src), "--dst", str(dst)], log_dir=tmp_path)
    assert code == 0
    text = (tmp_path / "运行日志.txt").read_text(encoding="utf-8-sig")
    assert "全部完成：成功 0 张，失败 0 张" in text
