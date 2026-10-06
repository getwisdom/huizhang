"""GUI 后台线程：信号序列与取消在单张边界生效（假任务驱动，不建窗口）。"""

import time

from PyQt6.QtCore import QThread

from koutu.gui.worker import BatchWorker


def _collect(worker):
    events = []
    worker.log_line.connect(lambda s: events.append(("log", s)))
    worker.progress.connect(lambda d, t: events.append(("progress", d, t)))
    worker.finished.connect(lambda ok, f, c: events.append(("finished", ok, f, c)))
    worker.failed.connect(lambda s: events.append(("failed", s)))
    return events


def test_worker_signal_sequence(qapp):
    def task(emit, progress, cancel):
        emit("[完成] a")
        progress(1, 2)
        emit("[完成] b")
        progress(2, 2)
        return 2, 0, False

    w = BatchWorker(task)
    events = _collect(w)
    w.run()
    assert events == [
        ("log", "[完成] a"),
        ("progress", 1, 2),
        ("log", "[完成] b"),
        ("progress", 2, 2),
        ("finished", 2, 0, False),
    ]


def test_worker_cancel_at_boundary(qapp):
    holder = {}

    def task(emit, progress, cancel):
        emit("[完成] 第1张")
        holder["w"].request_cancel()  # 在单张边界处请求取消
        if cancel():
            return 1, 0, True
        emit("[完成] 第2张")
        return 2, 0, False

    w = BatchWorker(task)
    holder["w"] = w
    events = _collect(w)
    w.run()
    assert ("finished", 1, 0, True) in events
    assert all(not (e[0] == "log" and "第2张" in e[1]) for e in events)


def test_worker_cancel_before_start_skips_all(qapp):
    def task(emit, progress, cancel):
        for i in range(3):
            if cancel():
                return i, 0, True
            emit(f"[完成] {i}")
        return 3, 0, False

    w = BatchWorker(task)
    w.request_cancel()
    events = _collect(w)
    w.run()
    assert events == [("finished", 0, 0, True)]


def test_worker_failure_emits_failed(qapp):
    def task(emit, progress, cancel):
        raise RuntimeError("炸了")

    w = BatchWorker(task)
    events = _collect(w)
    w.run()
    assert events[-1][0] == "failed"
    assert "炸了" in events[-1][1]


def test_worker_runs_in_qthread(qapp):
    def task(emit, progress, cancel):
        emit("[完成] x")
        progress(1, 1)
        return 1, 0, False

    w = BatchWorker(task)
    thread = QThread()
    done = []
    w.finished.connect(lambda ok, f, c: done.append((ok, f, c)))
    w.finished.connect(thread.quit)
    w.moveToThread(thread)
    thread.started.connect(w.run)
    thread.start()

    deadline = time.time() + 10
    while not done and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    thread.wait(5000)
    assert done == [(1, 0, False)]
