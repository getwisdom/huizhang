"""设置（QSettings ini）：打包版存程序根 koutu.ini，不可写时回退 %APPDATA%\\koutu\\koutu.ini。

QSettings 延迟导入：CLI 场景不触发 Qt。
"""

from __future__ import annotations

import os
from pathlib import Path

from . import paths


def settings_path() -> Path:
    return paths.program_root() / paths.SETTINGS_NAME


def fallback_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home())))
    return base / "koutu" / paths.SETTINGS_NAME


def open_settings():
    """返回 QSettings 实例；优先程序根 ini，不可写时回退到用户目录。"""
    from PyQt6.QtCore import QSettings

    primary = settings_path()
    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        with open(primary, "a", encoding="utf-8"):
            pass  # 可写性探测
        target = primary
    except OSError:
        target = fallback_path()
        target.parent.mkdir(parents=True, exist_ok=True)
    return QSettings(str(target), QSettings.Format.IniFormat)
