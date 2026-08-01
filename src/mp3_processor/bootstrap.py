"""根目录入口脚本共用的启动接线。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger, setup_logger
from mp3_processor.config_loader import load_config
from mp3_processor.context import AppContext


def bootstrap_context(entry_file: str, config_file: str = "config.yaml") -> AppContext:
    project_root = Path(entry_file).resolve().parent
    config_path = Path(config_file)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    config = load_config(config_path)
    app_config = config.get("app", {})
    setup_logger(
        log_level=app_config.get("log_level", "INFO"),
        log_file=project_root / "log" / f"{Path(entry_file).stem}.log",
    )
    return AppContext(project_root, config, get_logger(Path(entry_file).stem))
