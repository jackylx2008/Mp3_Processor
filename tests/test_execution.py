from __future__ import annotations

from pathlib import Path

import pytest

from mp3_processor.execution import CancellationToken, ProgressEvent, TaskCancelled, report_progress


def test_cancellation_token_raises_after_cancel() -> None:
    token = CancellationToken()

    token.raise_if_cancelled()
    token.cancel()

    assert token.cancelled
    with pytest.raises(TaskCancelled, match="任务已取消"):
        token.raise_if_cancelled()


def test_report_progress_sends_structured_event() -> None:
    events: list[ProgressEvent] = []
    item = Path("track.m4a")

    report_progress(events.append, "running", "正在转换", current=2, total=5, item=item)

    assert events == [ProgressEvent("running", "正在转换", 2, 5, item)]
