"""主窗口：三页签（抠图 / 排版 / 去水印占位）、后台线程、进度、取消、设置记忆。

- 线程模型与信号：见 design.md D3（同一时刻只允许一个任务；运行中切页签不中断）。
- 设置：QSettings(IniFormat)，程序根 koutu.ini 优先、不可写时回退 %APPDATA%\\koutu\\koutu.ini（D4）。
- 日志：与 CLI 同源落盘（程序根 运行日志.txt / 排版日志.txt），日志视图显示统计行原文。
- 目录选择（flexible-io）：输入/输出目录可编辑 + 浏览/恢复默认；任务与「打开输出目录」
  用当前选择；四键记忆（不可用回退默认并提示）；运行期锁定。
- 关窗保护（flexible-io D5/P0-3）：任务运行中关窗先中文确认（「继续等待 / 取消任务并退出」），
  不销毁运行中的线程；选退出=先请求取消、边界收束后关闭。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget

from .. import paths
from ..config import open_settings
from ..core import layout as layout_core
from . import dirselect
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
        self.cutout_page.btn_open.clicked.connect(self.open_cutout_output)
        self.layout_page.btn_open.clicked.connect(self.open_layout_output)

        self._thread: QThread | None = None
        self._worker: BatchWorker | None = None
        self._active_page = None
        self._kind = ""
        self._close_pending = False

        self.settings = open_settings()
        self._load_settings()
        self._ensure_data_dirs()

    # ------------------------------------------------------------- 启动任务
    def start_cutout(self) -> None:
        if self._thread is not None:  # 同一时刻只允许一个任务
            return
        root = paths.program_root()
        page = self.cutout_page
        picked = self._resolve_dirs(page)
        if picked is None:  # 五类校验失败：中文提示、任务不启动（flexible-io D2）
            return
        src, dst = picked
        page.clear_log()
        page.set_status("正在抠图…")
        task = make_cutout_task(
            src,
            dst,
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
        picked = self._resolve_dirs(page)
        if picked is None:
            return
        src, dst = picked
        page.clear_log()
        page.set_status("正在排版…")
        task = make_layout_task(
            root / paths.DEMO_NAME,
            src,
            dst,
            anchors=bool(page.chk_anchors.isChecked()),
            anchor_style=page.anchor_style(),
            # 安全规则（flexible-io D3）：仅默认「已排版」清空旧 *.png
            clean_old=paths.is_default_layout_dir(dst),
            log_path=root / paths.LOG_LAYOUT,
        )
        self._begin(task, page, "排版")

    def _resolve_dirs(self, page):
        """任务启动前的目录校验（五类中文报错、任务不启动；flexible-io D2）。"""
        root = paths.program_root()
        src = page.ed_src.value()
        dst = page.ed_dst.value()
        err = dirselect.validate_task_dirs(src, dst, root=root)
        if err:
            QMessageBox.warning(self, "目录不可用", err)
            return None
        return src, dst

    def _begin(self, task, page, kind: str) -> None:
        self._kind = kind
        self._active_page = page
        for p in (self.cutout_page, self.layout_page):
            p.set_busy(True, p is page)

        thread = QThread(self)
        worker = BatchWorker(task)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_line.connect(lambda text, p=page: self._on_log_line(p, text))
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

    def _on_log_line(self, page, text: str) -> None:
        """日志行上屏；「运行前」计数提示同时显示在状态行（不打断，flexible-io D4）。"""
        page.append_log(text)
        if text.startswith("运行前"):
            page.set_status(text)

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
        if self._close_pending:  # 关窗确认里选了「取消任务并退出」：收束后关闭
            self._close_pending = False
            self.close()

    # ------------------------------------------------------------- 杂项
    def open_cutout_output(self) -> None:
        """打开抠图当前选择的输出目录（跟随选择；flexible-io D8）。"""
        self._open_dir(self.cutout_page.ed_dst.value())

    def open_layout_output(self) -> None:
        """打开排版当前选择的输出目录（跟随选择；flexible-io D8）。"""
        self._open_dir(self.layout_page.ed_dst.value())

    def _open_dir(self, directory: Path) -> None:
        """缺目录按创建规则处理并中文提示；创建不了不打开（flexible-io D2/D8）。"""
        d = Path(directory)
        err = dirselect.ensure_output_dir(d, paths.program_root())
        if err:
            QMessageBox.warning(self, "目录不可用", err)
            return
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
        self.layout_page.set_anchor_style(
            str(s.value("layout/anchor_style", layout_core.ANCHOR_STYLE_TRIANGLE))
        )
        # 目录四键记忆（flexible-io D1）：不可用回退默认并中文提示
        self._load_dir_choice("cutout/src", self.cutout_page.ed_src, self.cutout_page)
        self._load_dir_choice("cutout/dst", self.cutout_page.ed_dst, self.cutout_page)
        self._load_dir_choice("layout/src", self.layout_page.ed_src, self.layout_page)
        self._load_dir_choice("layout/dst", self.layout_page.ed_dst, self.layout_page)

    def _load_dir_choice(self, key: str, row, page) -> None:
        """恢复记忆目录；不可用时回退默认并在界面给出中文提示（flexible-io D1）。"""
        raw = self.settings.value(key)
        if raw is None:
            return
        text = str(raw).strip()
        if not text:
            return
        resolved = paths.resolve_dir(paths.program_root(), text)
        if self._dir_usable(resolved, row.is_output):
            row.edit.setText(text)
            return
        row.reset_to_default()
        hint = f"上次使用的目录不可用，已恢复默认：{text}"
        page.append_log(f"[提示] {hint}")
        page.set_status(hint)

    @staticmethod
    def _dir_usable(resolved: Path, is_output: bool) -> bool:
        """记忆值可用性：输入须存在；输出须存在或可（按规则）创建。"""
        drive = resolved.drive
        if drive and not Path(drive + "\\").exists():
            return False
        if resolved.exists():
            return resolved.is_dir()
        if is_output:
            return resolved.parent.is_dir()
        return False

    def save_settings(self) -> None:
        s = self.settings
        s.setValue("ui/geometry", self.saveGeometry())
        s.setValue("ui/last-tab", self.tabs.currentIndex())
        s.setValue("cutout/scan-t", float(self.cutout_page.spin_scan_t.value()))
        s.setValue("cutout/feather", int(self.cutout_page.spin_feather.value()))
        s.setValue("layout/anchors", bool(self.layout_page.chk_anchors.isChecked()))
        s.setValue("layout/anchor_style", self.layout_page.anchor_style())
        s.setValue("cutout/src", self.cutout_page.ed_src.text())
        s.setValue("cutout/dst", self.cutout_page.ed_dst.text())
        s.setValue("layout/src", self.layout_page.ed_src.text())
        s.setValue("layout/dst", self.layout_page.ed_dst.text())
        s.sync()

    def closeEvent(self, event) -> None:  # noqa: N802（Qt 覆写）
        if self._thread is not None:  # 任务运行中关窗保护（flexible-io D5/P0-3）
            quit_now = self._confirm_quit_during_task()
            if self._thread is None:  # 确认对话期间任务已收束 → 按普通关闭处理
                self.save_settings()
                super().closeEvent(event)
                return
            if quit_now:
                self._close_pending = True
                self.cancel_task()  # 先取消；线程 finished 后 _on_thread_finished 关闭
            event.ignore()
            return
        self.save_settings()
        super().closeEvent(event)

    def _confirm_quit_during_task(self) -> bool:
        """关窗中文确认：True=取消任务并退出；False=继续等待（保持窗口）。"""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("任务正在运行")
        box.setText("任务正在运行：关闭窗口前请选择——继续等待任务完成，或取消任务并退出。")
        btn_wait = box.addButton("继续等待", QMessageBox.ButtonRole.RejectRole)
        btn_quit = box.addButton("取消任务并退出", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(btn_wait)
        box.exec()
        return box.clickedButton() is btn_quit


def launch(argv=None) -> int:
    """创建应用与主窗口并进入事件循环（双击入口）。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(list(argv) if argv else [])
    window = MainWindow()
    window.show()
    return app.exec()
