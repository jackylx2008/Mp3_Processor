"""入口层、编排层和模块层共享的应用上下文。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppContext:
    project_root: Path
    config: dict[str, Any]
    logger: logging.Logger

    def flow_config(self, name: str) -> dict[str, Any]:
        flows = self.config.get("flows", {})
        value = flows.get(name, {})
        if not isinstance(value, dict):
            raise ValueError(f"flows.{name} 必须是映射")
        return value

    def resolve_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else self.project_root / path
