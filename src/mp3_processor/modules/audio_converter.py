"""基于 FFmpeg 的单文件音频转换能力。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class AudioConversionError(RuntimeError):
    """音频转换失败。"""


def require_ffmpeg(executable: str = "ffmpeg") -> str:
    """返回 FFmpeg 路径，不可用时抛出清晰异常。"""
    resolved = shutil.which(executable)
    if not resolved:
        raise FileNotFoundError(f"找不到 FFmpeg: {executable}")
    return resolved


def convert_to_mp3(
    source: Path,
    destination: Path,
    *,
    bitrate: str = "192k",
    overwrite: bool = False,
    ffmpeg_executable: str = "ffmpeg",
) -> Path:
    """将一个音频/视频文件转换为 MP3，不删除源文件。"""
    if not source.is_file():
        raise FileNotFoundError(f"输入文件不存在: {source}")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        require_ffmpeg(ffmpeg_executable),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if overwrite else "-n",
        "-i",
        str(source),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        destination.unlink(missing_ok=True)
        message = completed.stderr.strip() or "FFmpeg 未返回错误详情"
        raise AudioConversionError(f"转换失败 {source}: {message}")
    return destination


def validate_audio(path: Path, ffmpeg_executable: str = "ffmpeg") -> bool:
    """尝试解码一秒音频，用于快速验证输出文件。"""
    command = [
        require_ffmpeg(ffmpeg_executable),
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(path),
        "-t",
        "1",
        "-f",
        "null",
        "-",
    ]
    return subprocess.run(command, capture_output=True).returncode == 0
