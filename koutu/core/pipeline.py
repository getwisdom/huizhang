"""批次执行器：确定性遍历、失败隔离、进度回调、协作式取消（单张文件边界生效）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional


@dataclass
class BatchSummary:
    total: int = 0
    ok: int = 0
    fail: int = 0
    cancelled: bool = False


def execute_batch(
    names: Iterable,
    process_one: Callable[[object], str],
    *,
    emit: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> BatchSummary:
    """顺序执行批处理。

    - `process_one(name)` 返回一条日志行；以 `[完成]` 开头计成功，其余计失败；
      抛出的异常被捕获为失败行（单张失败不中断整批）。
    - `cancel()` 为真时在「单张文件边界」停止（当张完成后）。
    """
    items = list(names)
    summary = BatchSummary(total=len(items))
    for idx, name in enumerate(items):
        if cancel is not None and cancel():
            summary.cancelled = True
            break
        try:
            line = process_one(name)
        except Exception as exc:  # 失败隔离：绝不中断整批
            line = f"[失败] {name}  处理异常: {exc}"
        if emit is not None:
            emit(line)
        if line.startswith("[完成]"):
            summary.ok += 1
        else:
            summary.fail += 1
        if on_progress is not None:
            on_progress(idx + 1, summary.total)
    return summary
