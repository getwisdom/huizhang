"""设置存储：程序根 koutu.ini 优先、不可写回退 %APPDATA%（口径见 design.md D4）。"""

from pathlib import Path

from koutu import config


def test_settings_in_program_root(tmp_path, monkeypatch):
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    assert config.settings_path() == tmp_path / "koutu.ini"

    s = config.open_settings()
    s.setValue("cutout/scan-t", 60)
    s.sync()
    assert (tmp_path / "koutu.ini").is_file()

    # 重启（重新打开）后仍能读回
    s2 = config.open_settings()
    assert int(s2.value("cutout/scan-t")) == 60


def test_settings_fallback_when_not_writable(tmp_path, monkeypatch):
    blocked = tmp_path / "blocked"
    blocked.mkdir()  # 以目录冒充文件路径：open(..., "a") 会抛 OSError
    fallback = tmp_path / "ap" / "koutu" / "koutu.ini"
    monkeypatch.setattr(config, "settings_path", lambda: blocked)
    monkeypatch.setattr(config, "fallback_path", lambda: fallback)

    s = config.open_settings()
    assert Path(s.fileName()) == fallback
    assert fallback.parent.is_dir()
