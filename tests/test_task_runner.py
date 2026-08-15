from __future__ import annotations

from time import monotonic, sleep

from mp3_processor.execution import ProgressEvent
from mp3_processor.gui.task_runner import TaskRunner
from mp3_processor.results import FlowResult


def wait_for_runner(runner: TaskRunner) -> list[str]:
    deadline = monotonic() + 2
    kinds: list[str] = []
    while monotonic() < deadline:
        kinds.extend(message.kind for message in runner.drain())
        if not runner.active:
            kinds.extend(message.kind for message in runner.drain())
            return kinds
        sleep(0.01)
    raise AssertionError("后台任务未按期结束")


def test_task_runner_publishes_progress_and_result() -> None:
    runner = TaskRunner()

    def task(token, progress):
        progress(ProgressEvent("running", "处理中", 1, 1))
        return FlowResult(discovered=1, succeeded=1)

    assert runner.start("测试任务", task)
    kinds = wait_for_runner(runner)

    assert kinds == ["started", "progress", "completed"]


def test_task_runner_cancels_cooperatively() -> None:
    runner = TaskRunner()

    def task(token, progress):
        while True:
            token.raise_if_cancelled()
            sleep(0.01)

    assert runner.start("可取消任务", task)
    assert runner.cancel()

    assert wait_for_runner(runner)[-1] == "cancelled"
