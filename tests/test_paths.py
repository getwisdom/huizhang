"""程序根解析：源码版 = 仓库根；打包版 = exe 所在目录。"""

import sys
from pathlib import Path

from koutu import paths


def test_program_root_source_mode():
    root = paths.program_root()
    assert (root / "koutu" / "__init__.py").is_file()
    assert (root / "openspec" / "config.yaml").is_file()


def test_program_root_frozen(monkeypatch, tmp_path):
    exe = tmp_path / "koutu.exe"
    exe.write_bytes(b"stub")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert paths.program_root() == exe.resolve().parent


def test_resolve_dir(tmp_path):
    assert paths.resolve_dir(tmp_path, "底图") == tmp_path / "底图"
    absolute = tmp_path / "x"
    assert paths.resolve_dir(paths.program_root(), str(absolute)) == absolute
