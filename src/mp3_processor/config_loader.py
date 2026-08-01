"""统一加载 common.env、环境变量和 YAML 配置。"""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Any

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?}")


def load_env_file(path: Path) -> None:
    """加载简单 dotenv 文件；已有环境变量优先。"""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def load_config(config_path: Path, env_path: Path | None = None) -> dict[str, Any]:
    """读取 YAML，并递归展开 `${ENV_VAR:-default}`。"""
    load_env_file(env_path or config_path.parent / "common.env")
    _set_cloudstation_root()
    if not config_path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("config.yaml 顶层必须是映射")
    return _expand_value(raw)


def _expand_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_value(item) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        resolved = os.getenv(name, default)
        if resolved is None:
            raise ValueError(f"环境变量未设置且没有默认值: {name}")
        return resolved

    expanded = ENV_PATTERN.sub(replace, value)
    return str(Path(expanded).expanduser()) if expanded else ""


def _set_cloudstation_root() -> None:
    if os.getenv("CLOUDSTATION_ROOT"):
        return
    names = {
        "windows": ("CLOUDSTATION_ROOT_WINDOWS",),
        "darwin": ("CLOUDSTATION_ROOT_MACOS", "CLOUDSTATION_ROOT_DARWIN"),
        "linux": ("CLOUDSTATION_ROOT_LINUX",),
    }.get(platform.system().lower(), ())
    for name in names:
        if value := os.getenv(name):
            os.environ["CLOUDSTATION_ROOT"] = value
            return
    os.environ["CLOUDSTATION_ROOT"] = str(Path("~/CloudStation").expanduser())
