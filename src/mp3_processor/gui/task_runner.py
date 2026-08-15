"""在后台线程执行工作流，并通过线程安全队列传递 UI 事件。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Literal

from mp3_processor.execution import CancellationToken, ProgressCallback, TaskCancelled
from mp3_processor.results import FlowResult


MessageKind = Literal["started", "progress", "log", "completed", "cancelled", "failed"]
Task = Callable[[CancellationToken, ProgressCallback], FlowResult]


@dataclass(frozen=True)
class TaskMessage:
    kind: MessageKind
    payload: object = None


class TaskRunner:
    """管理单个后台任务；所有 UI 更新由主线程消费消息后完成。"""

    def __init__(self) -> None:
        self._messages: Queue[TaskMessage] = Queue()
        self._lock = Lock()
        self._active = False
        self._token: CancellationToken | None = None

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    def start(self, name: str, task: Task) -> bool:
        with self._lock:
            if self._active:
                return False
            self._active = True
            self._token = CancellationToken()
            token = self._token
        thread = Thread(target=self._run, args=(name, task, token), daemon=True)
        thread.start()
        return True

    def cancel(self) -> bool:
        with self._lock:
            if not self._active or self._token is None:
                return False
            self._token.cancel()
            return True

    def post_log(self, message: str) -> None:
        self._messages.put(TaskMessage("log", message))

    def drain(self) -> list[TaskMessage]:
        messages: list[TaskMessage] = []
        while True:
            try:
                messages.append(self._messages.get_nowait())
            except Empty:
                return messages

    def _run(self, name: str, task: Task, token: CancellationToken) -> None:
        self._messages.put(TaskMessage("started", name))
        try:
            result = task(token, lambda event: self._messages.put(TaskMessage("progress", event)))
            token.raise_if_cancelled()
            self._messages.put(TaskMessage("completed", result))
        except TaskCancelled as exc:
            self._messages.put(TaskMessage("cancelled", str(exc)))
        except Exception as exc:
            logging.getLogger(__name__).exception("后台任务失败: %s", name)
            self._messages.put(TaskMessage("failed", exc))
        finally:
            with self._lock:
                self._active = False
                self._token = None


class QueueLogHandler(logging.Handler):
    """将项目日志复制到 GUI 消息队列。"""

    def __init__(self, sink: Callable[[str], None]) -> None:
        super().__init__()
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._sink(self.format(record))
        except Exception:
            self.handleError(record)
