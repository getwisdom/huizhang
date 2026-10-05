"""中文日志装配：固定文件写入（UTF-8 带 BOM，便于记事本直接打开）。"""

from __future__ import annotations

from pathlib import Path


def write_log_file(path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(text)


def fmt_num(v) -> str:
    """按旧日志习惯输出数字：整数不带小数点（45.0 → "45"）。"""
    f = float(v)
    if f.is_integer():
        return str(int(f))
    return str(f)
