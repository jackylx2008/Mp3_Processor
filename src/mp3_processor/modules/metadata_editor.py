"""MP3 与 M4A 元数据读写能力。"""

from __future__ import annotations

import re
from pathlib import Path

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


LEADING_EPISODE_ZERO = re.compile(r"(第)0+(\d+)(集)")


def title_from_filename(path: Path) -> str:
    """使用文件名作为标题，并清理“第001集”中的多余零。"""
    return LEADING_EPISODE_ZERO.sub(r"\1\2\3", path.stem)


def update_audio_tags(
    path: Path,
    *,
    artist: str | None = None,
    album: str | None = None,
    title: str | None = None,
) -> None:
    """更新一个 MP3 或 M4A 文件的常用标签。"""
    title = title or title_from_filename(path)
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        audio = MP3(path, ID3=EasyID3)
        if audio.tags is None:
            audio.add_tags()
        audio["title"] = title
        if artist:
            audio["artist"] = artist
        if album:
            audio["album"] = album
        audio.save()
        return
    if suffix == ".m4a":
        audio = MP4(path)
        audio["\xa9nam"] = [title]
        if artist:
            audio["\xa9ART"] = [artist]
        if album:
            audio["\xa9alb"] = [album]
        audio.save()
        return
    raise ValueError(f"不支持写入元数据的格式: {path.suffix}")


def album_for_file(path: Path, root: Path, base_album: str | None, include_folder: bool) -> str | None:
    """根据配置组合基础专辑名和文件所在目录名。"""
    if not include_folder:
        return base_album
    folder = path.parent.name if path.parent != root else root.name
    return " ".join(part for part in (base_album, folder) if part) or None
