"""程序根与目录契约路径（design.md D5；目录名不可重命名）。"""

from __future__ import annotations

import sys
from pathlib import Path

# —— 数据目录契约（中文名固定，见 pipeline-orchestration 规格） ——
DIR_INPUT = "原图"          # 抠图输入
DIR_BASE = "底图"           # 抠图输出 / 排版的输入
DIR_LAYOUT = "已排版"       # 排版输出
DEMO_NAME = "排版demo.png"  # 排版模板（可替换资源）

# —— 固定日志文件名（写入程序根） ——
LOG_CUTOUT = "运行日志.txt"
LOG_LAYOUT = "排版日志.txt"

# —— 设置文件（QSettings ini） ——
SETTINGS_NAME = "koutu.ini"

SUPPORTED_IMAGE_EXTS = ("jpg", "jpeg", "png", "bmp", "gif", "tif", "tiff")


def program_root() -> Path:
    """程序根：打包版 = exe 所在目录；源码版 = 仓库根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resolve_dir(root, value) -> Path:
    """相对路径按程序根解析；绝对路径直接使用。"""
    p = Path(value)
    return p if p.is_absolute() else Path(root) / p
