"""文件发现与路径映射能力。"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path


AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".mp4", ".wma"})
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})


def iter_files(
    root: Path,
    extensions: Iterable[str],
    *,
    recursive: bool = True,
    max_depth: int = 0,
) -> Iterator[Path]:
    """按路径稳定排序返回指定扩展名的文件；max_depth=0 表示不限制。"""
    if not root.is_dir():
        raise NotADirectoryError(f"目录不存在: {root}")
    normalized = {suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}" for suffix in extensions}
    iterator = root.rglob("*") if recursive else root.glob("*")
    files = (path for path in iterator if path.is_file() and path.suffix.lower() in normalized)
    if max_depth > 0:
        files = (path for path in files if len(path.relative_to(root).parts) - 1 <= max_depth)
    yield from sorted(files, key=lambda path: str(path).casefold())


def output_path_for(source: Path, source_root: Path, output_root: Path, suffix: str) -> Path:
    """保留输入目录层级并替换扩展名。"""
    relative = source.relative_to(source_root)
    return (output_root / relative).with_suffix(suffix)
