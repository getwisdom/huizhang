"""主窗口：三页签（抠图 / 排版 / 去水印占位）、后台线程、进度、取消、设置记忆。

- 线程模型与信号：见 design.md D3（同一时刻只允许一个任务；运行中切页签不中断）。
- 设置：QSettings(IniFormat)，程序根 koutu.ini 优先、不可写时回退 %APPDATA%\\koutu\\koutu.ini（D4）。
- 日志：与 CLI 同源落盘（程序根 运行日志.txt / 排版日志.txt），日志视图显示统计行原文。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget

from .. import paths
from ..config import open_settings
from .pages import CutoutPage, LayoutPage, WatermarkPage
from .worker import BatchWorker, make_cutout_task, make_layout_task

WINDOW_TITLE = "koutu · 徽章处理工具"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(880, 640)

        root = paths.program_root()
        self.cutout_page = CutoutPage(root, self)
        self.layout_page = LayoutPage(root, self)
        self.watermark_page = WatermarkPage(self)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self.cutout_page, "抠图")
        self.tabs.addTab(self.layout_page, "排版")
        self.tabs.addTab(self.watermark_page, "去水印")
        self.setCentralWidget(self.tabs)

        self.cutout_page.btn_start.clicked.connect(self.start_cutout)
        self.layout_page.btn_start.clicked.connect(self.start_layout)
        for page in (self.cutout_page, self.layout_page):
            page.btn_cancel.clicked.connect(self.cancel_task)
        self.cutout_page.btn_open.clicked.connect(
            lambda: self._open_dir(paths.program_root() / paths.DIR_BASE)
        )
        self.layout_page.btn_open.clicked.connect(
            lambda: self._open_dir(paths.program_root() / paths.DIR_LAYOUT)
        )

        self._thread: QThread | None = None
        self._worker: BatchWorker | None = None
        self._active_page = None
        self._kind = ""

        self.settings = open_settings()
        self._load_settings()
        self._ensure_data_dirs()

    # ------------------------------------------------------------- 启动任务
    def start_cutout(self) -> None:
        if self._thread is not None:  # 同一时刻只允许一个任务
            return
        root = paths.program_root()
        page = self.cutout_page
        page.clear_log()
        page.set_status("正在抠图…")
        task = make_cutout_task(
            root / paths.DIR_INPUT,
            root / paths.DIR_BASE,
            scan_t=float(page.spin_scan_t.value()),
            feather=int(page.spin_feather.value()),
            margin=4,
            log_path=root / paths.LOG_CUTOUT,
        )
        self._begin(task, page, "抠图")

    def start_layout(self) -> None:
        if self._thread is not None:
            return
        root = paths.program_root()
        page = self.layout_page
        page.clear_log()
        page.set_status("正在排版…")
        task = make_layout_task(
            root / paths.DEMO_NAME,
            root / paths.DIR_BASE,
            root / paths.DIR_LAYOUT,
            anchors=bool(page.chk_anchors.isChecked()),
            log_path=root / paths.LOG_LAYOUT,
        )
        self._begin(task, page, "排版")

    def _begin(self, task, page, kind: str) -> None:
        self._kind = kind
        self._active_page = page
        for p in (self.cutout_page, self.layout_page):
            p.set_busy(True, p is page)

        thread = QThread(self)
        worker = BatchWorker(task)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_line.connect(page.append_log)
        worker.progress.connect(page.set_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    def cancel_task(self) -> None:
        if self._worker is None:
            return
        self._worker.request_cancel()
        if self._active_page is not None:
            self._active_page.btn_cancel.setEnabled(False)
            self._active_page.set_status("正在取消：将在当前处理完成后停止…")

    # ------------------------------------------------------------- 任务回调
    def _on_finished(self, ok: int, fail: int, cancelled: bool) -> None:
        page = self._active_page
        if page is None:
            return
        if self._kind == "抠图":
            if cancelled:
                text = f"抠图已取消：成功 {ok} 张，失败 {fail} 张"
            else:
                text = f"抠图完成：成功 {ok} 张，失败 {fail} 张"
            if fail:
                text += "（失败详情见日志）"
        else:
            if fail:
                text = "排版失败（详情见日志）"
            elif cancelled:
                text = f"排版已取消：已生成 {ok} 页（详情见日志）"
            else:
                text = f"排版完成：共 {ok} 页"
        page.set_status(text)

    def _on_failed(self, message: str) -> None:
        page = self._active_page
        if page is not None:
            page.append_log(f"[失败] {message}")
            page.set_status("任务失败（详情见日志）")
        QMessageBox.warning(self, "任务失败", message)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._active_page = None
        for p in (self.cutout_page, self.layout_page):
            p.set_busy(False, False)

    # ------------------------------------------------------------- 杂项
    def _open_dir(self, directory: Path) -> None:
        d = Path(directory)
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _ensure_data_dirs(self) -> None:
        """首次启动自动创建缺失的「原图」「底图」（只读环境不阻塞启动）。"""
        root = paths.program_root()
        for name in (paths.DIR_INPUT, paths.DIR_BASE):
            try:
                (root / name).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    def _load_settings(self) -> None:
        s = self.settings
        geo = s.value("ui/geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        try:
            idx = int(s.value("ui/last-tab", 0))
        except (TypeError, ValueError):
            idx = 0
        if 0 <= idx < self.tabs.count():
            self.tabs.setCurrentIndex(idx)
        try:
            self.cutout_page.spin_scan_t.setValue(float(s.value("cutout/scan-t", 45.0)))
        except (TypeError, ValueError):
            pass
        try:
            self.cutout_page.spin_feather.setValue(int(s.value("cutout/feather", 4)))
        except (TypeError, ValueError):
            pass
        try:
            self.layout_page.chk_anchors.setChecked(
                bool(s.value("layout/anchors", True, type=bool))
            )
        except (TypeError, ValueError):
            self.layout_page.chk_anchors.setChecked(True)

    def save_settings(self) -> None:
        s = self.settings
        s.setValue("ui/geometry", self.saveGeometry())
        s.setValue("ui/last-tab", self.tabs.currentIndex())
        s.setValue("cutout/scan-t", float(self.cutout_page.spin_scan_t.value()))
        s.setValue("cutout/feather", int(self.cutout_page.spin_feather.value()))
        s.setValue("layout/anchors", bool(self.layout_page.chk_anchors.isChecked()))
        s.sync()

    def closeEvent(self, event) -> None:  # noqa: N802（Qt 覆写）
        self.save_settings()
        super().closeEvent(event)


def launch(argv=None) -> int:
    """创建应用与主窗口并进入事件循环（双击入口）。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(list(argv) if argv else [])
    window = MainWindow()
    window.show()
    return app.exec()
