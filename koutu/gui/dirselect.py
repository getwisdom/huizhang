"""GUI 目录选择支持（flexible-io design D1/D2/D8）。

- 目录行 = 可编辑输入框 + 「浏览…」 + 「恢复默认」（默认值为程序根约定目录）；
- 相对路径按程序根解析，绝对路径原样使用；
- 校验在 GUI 层、任务启动前执行：五类中文报错、任务不启动（不直出英文异常原文）；
- 自定义输出目录只创建最后一级（父目录必须已存在）；默认目录照旧允许多级；
- 写入权限用「实际试写」探测（Windows 下 os.access 不可靠）。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from .. import paths

MAX_PATH_LEN = 259  # Windows 传统路径上限（校验口径，见 design D2）


class DirRow(QWidget):
    """输入/输出目录行：可编辑 + 浏览… + 恢复默认；相对路径按程序根解析。"""

    def __init__(self, root: Path, default_value: Path, *, is_output: bool = False, parent=None):
        super().__init__(parent)
        self.root = Path(root)
        self.default_value = Path(default_value)
        self.is_output = bool(is_output)
        self.edit = QLineEdit(str(self.default_value), self)
        self.btn_browse = QPushButton("浏览…", self)
        self.btn_reset = QPushButton("恢复默认", self)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.btn_browse)
        lay.addWidget(self.btn_reset)
        self.btn_browse.clicked.connect(self._browse)
        self.btn_reset.clicked.connect(self.reset_to_default)

    def text(self) -> str:
        return self.edit.text().strip()

    def value(self) -> Path:
        """当前选择的目录；空文本回退默认值；相对路径按程序根解析。"""
        text = self.text()
        if not text:
            return Path(self.default_value)
        return paths.resolve_dir(self.root, text)

    def reset_to_default(self) -> None:
        self.edit.setText(str(self.default_value))

    def _browse(self) -> None:
        start = self.value()
        chosen = QFileDialog.getExistingDirectory(
            self, "选择目录", str(start if start.is_dir() else self.root)
        )
        if chosen:
            self.edit.setText(chosen)


def _same_path(a: Path, b: Path) -> bool:
    """解析后的绝对路径比较（Windows 下大小写不敏感）。"""
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))


def _is_default_output(dst: Path, root: Path) -> bool:
    """输出目录是否属于默认集合（程序根 底图 / 已排版，按解析路径判定）。"""
    return _same_path(dst, Path(root) / paths.DIR_BASE) or _same_path(
        dst, Path(root) / paths.DIR_LAYOUT
    )


def ensure_output_dir(dst: Path, root: Path) -> str | None:
    """按创建规则确保输出目录存在；返回中文错误文案或 None。

    - 默认目录（程序根 底图 / 已排版）：缺失时按需多级创建（与既有行为一致）；
    - 自定义目录：只创建最后一级（父目录必须已存在），不隐式创建多级。
    """
    dst = Path(dst)
    if dst.exists():
        if not dst.is_dir():
            return f"输出路径不是文件夹：{dst}。请更换路径。"
        return None
    try:
        if _is_default_output(dst, root):
            dst.mkdir(parents=True, exist_ok=True)
        else:
            if not dst.parent.is_dir():
                return f"目录不存在，且无法创建：{dst}。请检查路径或选择其他目录。"
            dst.mkdir()
        return None
    except OSError:
        return f"目录不存在，且无法创建：{dst}。请检查路径或选择其他目录。"


def probe_writable(directory: Path) -> bool:
    """实际试写探测（临时文件创建后删除）；Windows 下 os.access 不可靠。"""
    try:
        fd, name = tempfile.mkstemp(prefix=".koutu_写探测_", dir=str(directory))
        os.close(fd)
        try:
            os.remove(name)
        except OSError:
            pass
        return True
    except OSError:
        return False


def validate_task_dirs(src: Path, dst: Path, *, root: Path) -> str | None:
    """任务启动前的五类校验；返回中文错误文案（任务不启动）或 None。

    五类：目录不存在（或无法创建）/ 无写入权限 / 盘符或路径无效 / 输出=输入 / 超长。
    """
    src = Path(src)
    dst = Path(dst)
    # 5) 路径过长
    for p in (src, dst):
        if len(str(p)) > MAX_PATH_LEN:
            return f"路径过长（超过 {MAX_PATH_LEN} 字符）：{p}。请缩短目录层级。"
    # 3) 盘符 / 路径无效
    for p in (src, dst):
        drive = p.drive
        if drive and not Path(drive + os.sep).exists():
            return f"盘符不存在：{drive}。请检查路径。"
    # 4) 输出目录与输入目录相同
    if _same_path(src, dst):
        return f"输出目录不能和输入目录相同：{src}。请更换其中一个。"
    # 1) 输入目录必须已存在（GUI 不自动创建自定义输入目录）
    if not src.exists():
        return f"输入目录不存在：{src}。请检查路径或选择其他目录。"
    if not src.is_dir():
        return f"输入路径不是文件夹：{src}。请选择其他目录。"
    # 输出目录创建（默认多级 / 自定义只建最后一级）
    err = ensure_output_dir(dst, root)
    if err:
        return err
    # 2) 写入权限（实际试写）
    if not probe_writable(dst):
        return f"目录没有写入权限：{dst}。请换一个目录或调整权限。"
    return None
