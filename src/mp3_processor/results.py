"""跨工作流使用的结构化运行结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FlowResult:
    discovered: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    outputs: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "discovered": self.discovered,
            "succeeded": self.succeeded,
            "skipped": self.skipped,
            "failed": self.failed,
            "outputs": [str(path) for path in self.outputs],
            "errors": self.errors,
        }
