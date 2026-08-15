"""工作流进度通知与协作式取消。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Literal


ProgressStage = Literal["scanning", "running", "completed"]


@dataclass(frozen=True)
class ProgressEvent:
    """从工作流发送给 CLI、GUI 或测试的结构化进度事件。"""

    stage: ProgressStage
    message: str
    current: int = 0
    total: int = 0
    item: Path | None = None


ProgressCallback = Callable[[ProgressEvent], None]


class TaskCancelled(RuntimeError):
    """任务在安全处理边界响应了取消请求。"""


class CancellationToken:
    """可在线程之间安全共享的取消标记。"""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise TaskCancelled("任务已取消")


def report_progress(
    callback: ProgressCallback | None,
    stage: ProgressStage,
    message: str,
    *,
    current: int = 0,
    total: int = 0,
    item: Path | None = None,
) -> None:
    """在调用方提供监听器时发布进度。"""
    if callback is not None:
        callback(ProgressEvent(stage, message, current, total, item))


def check_cancelled(token: CancellationToken | None) -> None:
    """在工作流的安全边界检查取消请求。"""
    if token is not None:
        token.raise_if_cancelled()
