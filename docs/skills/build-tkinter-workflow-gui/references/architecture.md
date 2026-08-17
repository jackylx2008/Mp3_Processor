# Architecture and execution patterns

Read this reference when adding or changing workflow services, progress, cancellation, task threading, logging, or configuration.

## Contents

- Execution events
- Cooperative cancellation
- Task runner
- Logging bridge
- Configuration and context
- Data safety

## Execution events

Use one immutable event shape across workflows:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Stage = Literal["scanning", "running", "completed"]

@dataclass(frozen=True)
class ProgressEvent:
    stage: Stage
    message: str
    current: int = 0
    total: int = 0
    item: Path | None = None
```

Publish events before scanning, after discovery, before each item, after each item, and at normal completion. Let the task runner own cancelled and failed terminal messages.

## Cooperative cancellation

Back the token with `threading.Event`:

```python
class TaskCancelled(RuntimeError):
    pass

class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise TaskCancelled("任务已取消")
```

Check at safe boundaries. If a module can process multiple sub-items, pass the token down and check between them. Re-raise `TaskCancelled` before broad `except Exception` handlers.

Do not claim instant cancellation when an external process or library call cannot be interrupted safely. State that the current item finishes first.

## Task runner

Keep task lifecycle independent of Tk:

```text
start(name, callable)
  ├─ reject if active
  ├─ create token
  ├─ worker emits started
  ├─ callable(token, progress_sink)
  └─ worker emits completed | cancelled | failed

main thread
  └─ after(100, drain_queue_and_render)
```

Protect active state and token with a lock. A daemon worker is acceptable only when the close handler waits for cooperative shutdown; otherwise use a non-daemon worker and an explicit join strategy.

Avoid worker calls to `messagebox`, `StringVar`, `Text`, `Progressbar`, or any other Tk object.

## Logging bridge

Attach one handler to the existing root logger:

```python
class QueueLogHandler(logging.Handler):
    def __init__(self, sink):
        super().__init__()
        self._sink = sink

    def emit(self, record):
        try:
            self._sink(self.format(record))
        except Exception:
            self.handleError(record)
```

The sink must only enqueue text. Render it from the main thread. Preserve rotating file handlers and avoid clearing unrelated handlers during config reload.

Cap retained UI lines to prevent unbounded memory growth. Delete oldest complete lines after insertion.

## Configuration and context

Load configuration before creating forms, then populate variables from `workflows.<name>`. On reload:

1. Refuse while a task is active.
2. Resolve the selected YAML path.
3. Validate top-level mappings and value types.
4. Replace the immutable application context.
5. Repopulate every tab.
6. Update log level and external-tool status.

Keep the context small: project root, expanded configuration, and logger. Service functions should receive runtime options explicitly; use configuration only for defaults.

## Data safety

- Default in-place operations to preview.
- Require an explicit write checkbox and confirmation dialog.
- Disable duplicate starts.
- Do not delete source files as part of conversion or splitting unless separately requested.
- Check all destination conflicts before multi-output operations when partial output would be confusing.
- Record individual failures in the result and continue only when the workflow contract allows it.
- On cancellation, remove only incomplete outputs that the current run created and can identify safely.
