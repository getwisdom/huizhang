"""CLI watermark 占位子命令：中文提示、退出码 2、不读写任何目录。"""

from koutu.cli.main import build_parser
from koutu.cli.main import main as cli_main


def test_parser_lists_watermark():
    assert "watermark" in build_parser().format_help()


def test_watermark_placeholder_message_and_code(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    code = cli_main(["watermark"])
    assert code == 2
    out = capsys.readouterr().out
    assert "后续版本提供" in out
    # 不读写任何目录：程序根保持空
    assert list(tmp_path.iterdir()) == []
