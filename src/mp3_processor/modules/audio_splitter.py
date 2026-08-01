"""音频切分与导出能力。"""

from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

from mp3_processor.modules.audio_converter import validate_audio


def split_audio(
    source: Path,
    output_dir: Path,
    *,
    duration_minutes: float,
    bitrate: str = "192k",
    overwrite: bool = False,
) -> list[Path]:
    """按固定分钟数切分音频，保留最后一个不足时长的片段。"""
    if duration_minutes <= 0:
        raise ValueError("duration_minutes 必须大于 0")
    audio = AudioSegment.from_file(source)
    duration_ms = int(duration_minutes * 60 * 1000)
    starts = list(range(0, len(audio), duration_ms))
    digits = max(2, len(str(len(starts))))
    output_dir.mkdir(parents=True, exist_ok=True)
    destinations = [
        output_dir / f"{source.stem}_part_{index:0{digits}d}.mp3"
        for index in range(1, len(starts) + 1)
    ]
    existing = next((path for path in destinations if path.exists()), None)
    if existing and not overwrite:
        raise FileExistsError(f"输出文件已存在: {existing}")

    outputs: list[Path] = []
    try:
        for start, destination in zip(starts, destinations, strict=True):
            audio[start : start + duration_ms].export(destination, format="mp3", bitrate=bitrate)
            if not validate_audio(destination):
                raise RuntimeError(f"切分结果无法解码: {destination}")
            outputs.append(destination)
    except Exception:
        if not overwrite:
            for path in outputs:
                path.unlink(missing_ok=True)
        raise
    return outputs
