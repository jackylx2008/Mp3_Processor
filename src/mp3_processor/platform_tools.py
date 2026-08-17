"""跨平台外部工具发现与配置。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def resolve_executable(value: str | Path, *, name: str) -> str:
    """解析命令名或显式路径，并返回可执行文件的绝对路径。"""
    candidate = os.path.expandvars(os.path.expanduser(os.fspath(value)))
    resolved = shutil.which(candidate)
    if resolved:
        return str(Path(resolved).resolve())

    path = Path(candidate)
    looks_like_path = path.is_absolute() or path.parent != Path(".")
    if looks_like_path:
        raise FileNotFoundError(f"{name} 可执行文件不存在或不可执行: {path}")
    raise FileNotFoundError(
        f"找不到 {name}: {candidate}。请使用项目根目录的 Conda 环境，"
        f"或通过配置提供 {name} 的可执行文件路径。"
    )
