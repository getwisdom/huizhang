"""后台线程任务：QThread + 信号（log_line / progress / finished / failed）。

线程模型与信号口径见 design.md D3：
- 任务在 QThread 中运行（Worker 对象 moveToThread），主线程只做界面；
- 取消 = 协作式（threading.Event），由内核在「单张文件边界」检查生效；
- finished(ok, fail, cancelled)：抠图=成功/失败张数；排版=已生成页数/失败标志。
"""

from __future__ import annotations

import threading
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from ..core import cutout as cutout_core
from ..core import layout as layout_core


class BatchWorker(QObject):
    """把一次批处理任务跑在后台线程里；GUI 与 CLI 共用同一内核路径。"""

    log_line = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, int, bool)  # ok / fail / cancelled
    failed = pyqtSignal(str)

    def __init__(self, task: Callable):
        super().__init__()
        self._task = task
        self._cancel_evt = threading.Event()

    def request_cancel(self) -> None:
        """请求取消；实际停止点在下一个「单张文件边界」。"""
        self._cancel_evt.set()

    def run(self) -> None:
        try:
            ok, fail, cancelled = self._task(
                self.log_line.emit, self.progress.emit, self._cancel_evt.is_set
            )
        except Exception as exc:  # 未捕获异常 → failed 信号（GUI 记日志 + 中文提示）
            self.failed.emit(f"发生错误：{exc}")
            return
        self.finished.emit(int(ok), int(fail), bool(cancelled))


def make_cutout_task(src, dst, *, scan_t, feather, margin, log_path) -> Callable:
    """构造抠图任务闭包（emit/progress/cancel 与 core 回调一一对应）。"""

    def task(emit, progress, cancel):
        summary, _text = cutout_core.run_cutout_batch(
            src,
            dst,
            scan_t=scan_t,
            feather=feather,
            margin=margin,
            log_path=log_path,
            emit=emit,
            on_progress=progress,
            cancel=cancel,
        )
        return summary.ok, summary.fail, summary.cancelled

    return task


def make_layout_task(demo, src, dst, *, anchors=True, anchor_style=None, log_path) -> Callable:
    """构造排版任务闭包；取消在「单页边界」生效，返回实际生成页数。"""
    style = anchor_style or layout_core.ANCHOR_STYLE_TRIANGLE

    def task(emit, progress, cancel):
        state = {"cancelled": False, "done": 0}

        def progress2(done, total):
            state["done"] = int(done)
            progress(done, total)

        def cancel_check():
            if cancel():
                state["cancelled"] = True
            return state["cancelled"]

        summary, _text = layout_core.run_layout_batch(
            demo,
            src,
            dst,
            anchors=anchors,
            anchor_style=style,
            log_path=log_path,
            emit=emit,
            progress=progress2,
            cancel=cancel_check,
        )
        if summary.error is not None:
            return state["done"], 1, False
        return state["done"], 0, state["cancelled"]

    return task
