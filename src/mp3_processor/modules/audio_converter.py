"""基于 FFmpeg 的单文件音频转换能力。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from mp3_processor.platform_tools import resolve_executable


class AudioConversionError(RuntimeError):
    """音频转换失败。"""


OUTPUT_CODECS = {
    "mp3": "libmp3lame",
    "m4a": "aac",
    "wma": "wmav2",
    "wav": "pcm_s16le",
    "flac": "flac",
    "ogg": "libvorbis",
}


def require_ffmpeg(executable: str = "ffmpeg") -> str:
    """返回 FFmpeg 路径，不可用时抛出清晰异常。"""
    return resolve_executable(executable, name="FFmpeg")


def convert_audio(
    source: Path,
    destination: Path,
    *,
    bitrate: str = "192k",
    overwrite: bool = False,
    ffmpeg_executable: str = "ffmpeg",
) -> Path:
    """按目标文件扩展名转换音频，不删除源文件。"""
    if not source.is_file():
        raise FileNotFoundError(f"输入文件不存在: {source}")
    if source.resolve() == destination.resolve(strict=False):
        raise ValueError(f"输入和输出不能是同一文件: {source}")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在: {destination}")

    output_type = destination.suffix.lower().lstrip(".")
    try:
        codec = OUTPUT_CODECS[output_type]
    except KeyError as exc:
        supported = ", ".join(OUTPUT_CODECS)
        raise ValueError(f"不支持的输出类型: {output_type or '<empty>'}；可选: {supported}") from exc

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
        codec,
    ]
    if output_type not in {"wav", "flac"}:
        command.extend(["-b:a", bitrate])
    command.append(str(destination))

    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        destination.unlink(missing_ok=True)
        message = completed.stderr.strip() or "FFmpeg 未返回错误详情"
        raise AudioConversionError(f"转换失败 {source}: {message}")
    return destination


def convert_to_mp3(
    source: Path,
    destination: Path,
    *,
    bitrate: str = "192k",
    overwrite: bool = False,
    ffmpeg_executable: str = "ffmpeg",
) -> Path:
    """兼容旧调用：将一个音频/视频文件转换为 MP3。"""
    if destination.suffix.lower() != ".mp3":
        raise ValueError("convert_to_mp3 的目标文件扩展名必须是 .mp3")
    return convert_audio(
        source,
        destination,
        bitrate=bitrate,
        overwrite=overwrite,
        ffmpeg_executable=ffmpeg_executable,
    )


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
