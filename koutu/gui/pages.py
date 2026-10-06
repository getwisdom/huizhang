"""三页签的界面部件：抠图 / 排版 / 去水印（入口占位）与共用骨架。

文案与禁用态口径见本变更 desktop-gui / watermark-removal delta：
- 「去水印」为入口占位页签：显示「后续版本提供」类中文说明、占位禁用态、不执行任何处理。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import paths


class TaskPage(QWidget):
    """抠图 / 排版共用骨架：只读路径展示 + 按钮 + 进度 + 日志（显示统计行原文）。"""

    start_text = "开始处理"

    def __init__(self, root: Path, parent=None):
        super().__init__(parent)
        self.root = Path(root)
        self.ed_paths: list[QLineEdit] = []

        self.form = QFormLayout()
        self.btn_start = QPushButton(self.start_text, self)
        self.btn_cancel = QPushButton("取消", self)
        self.btn_cancel.setEnabled(False)
        self.btn_open = QPushButton("打开输出目录", self)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m")
        self.status = QLabel("就绪", self)

        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_cancel)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_open)

        lay = QVBoxLayout(self)
        lay.addLayout(self.form)
        lay.addLayout(buttons)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)
        lay.addWidget(self.log, 1)

    # ------------------------------------------------------------- 构造辅助
    def add_path_row(self, label: str, value: Path) -> QLineEdit:
        ed = QLineEdit(str(value), self)
        ed.setReadOnly(True)
        self.form.addRow(label, ed)
        self.ed_paths.append(ed)
        return ed

    # ------------------------------------------------------------- 运行态/内容
    def set_busy(self, busy: bool, active: bool) -> None:
        """busy=有任务在跑；active=本页签是当前任务页。"""
        self.btn_start.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy and active)

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(text)

    def clear_log(self) -> None:
        self.log.clear()

    def set_progress(self, done: int, total: int) -> None:
        self.progress.setRange(0, max(1, int(total)))
        self.progress.setValue(int(done))

    def set_status(self, text: str) -> None:
        self.status.setText(text)


class CutoutPage(TaskPage):
    """抠图页签：扫描阈值 10–200（默认 45）、羽化宽度 0–20（默认 4）。"""

    start_text = "开始抠图"

    def __init__(self, root: Path, parent=None):
        super().__init__(root, parent)
        self.ed_src = self.add_path_row("输入（原图）：", self.root / paths.DIR_INPUT)
        self.ed_dst = self.add_path_row("输出（底图）：", self.root / paths.DIR_BASE)

        self.spin_scan_t = QDoubleSpinBox(self)
        self.spin_scan_t.setRange(10.0, 200.0)
        self.spin_scan_t.setDecimals(0)
        self.spin_scan_t.setSingleStep(1.0)
        self.spin_scan_t.setValue(45.0)
        self.spin_feather = QSpinBox(self)
        self.spin_feather.setRange(0, 20)
        self.spin_feather.setValue(4)

        params = QWidget(self)
        row = QHBoxLayout(params)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel("扫描阈值：", params))
        row.addWidget(self.spin_scan_t)
        row.addSpacing(12)
        row.addWidget(QLabel("羽化宽度：", params))
        row.addWidget(self.spin_feather)
        row.addStretch(1)
        self.form.addRow("参数：", params)


class LayoutPage(TaskPage):
    """排版页签：模板 + 底图 → 已排版（每页张数由模板槽位数决定）。

    参数面：「添加定位点」勾选框（默认勾选；QSettings 记忆；任务运行中禁用）。
    """

    start_text = "开始排版"

    def __init__(self, root: Path, parent=None):
        super().__init__(root, parent)
        self.ed_demo = self.add_path_row("模板（排版demo.png）：", self.root / paths.DEMO_NAME)
        self.ed_src = self.add_path_row("输入（底图）：", self.root / paths.DIR_BASE)
        self.ed_dst = self.add_path_row("输出（已排版）：", self.root / paths.DIR_LAYOUT)

        self.chk_anchors = QCheckBox("添加定位点", self)
        self.chk_anchors.setChecked(True)
        params = QWidget(self)
        row = QHBoxLayout(params)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.chk_anchors)
        row.addStretch(1)
        self.form.addRow("参数：", params)

    def set_busy(self, busy: bool, active: bool) -> None:
        """运行态：定位点勾选框随任务禁用（layout-anchors）。"""
        super().set_busy(busy, active)
        self.chk_anchors.setEnabled(not busy)


class WatermarkPage(QWidget):
    """去水印占位页签：文案定稿一句 + 占位禁用态；不执行任何处理。"""

    PLACEHOLDER_TEXT = "本功能后续版本提供"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(self.PLACEHOLDER_TEXT, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.btn_start = QPushButton("开始去水印", self)
        self.btn_start.setEnabled(False)  # 占位禁用态：不提供可用处理入口

        lay = QVBoxLayout(self)
        lay.addStretch(1)
        lay.addWidget(self.label)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.btn_start)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
