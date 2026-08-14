"""批量转换音频工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.modules.audio_converter import convert_to_mp3, validate_audio
from mp3_processor.modules.files import iter_files, output_path_for
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_files: int | None = None,
) -> FlowResult:
    """发现源文件、转换为 MP3 并验证输出。"""
    config = context.flow_config("convert_audio")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    target_root = context.resolve_path(output_dir or config.get("output_dir", "output/converted"))
    extensions = config.get("input_extensions", ["m4a", "mp4", "wma"])
    files = list(
        iter_files(
            source_root,
            extensions,
            recursive=bool(config.get("recursive", True)),
            max_depth=int(config.get("max_depth", 0)),
        )
    )
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]

    result = FlowResult(discovered=len(files))
    ffmpeg_executable = str(config.get("ffmpeg", "ffmpeg"))
    for source in files:
        destination = output_path_for(source, source_root, target_root, ".mp3")
        if destination.exists() and not bool(config.get("overwrite", False)):
            logger.info("跳过已存在文件: %s", destination)
            result.skipped += 1
            continue
        try:
            convert_to_mp3(
                source,
                destination,
                bitrate=str(config.get("bitrate", "192k")),
                overwrite=bool(config.get("overwrite", False)),
                ffmpeg_executable=ffmpeg_executable,
            )
            if bool(config.get("validate_output", True)) and not validate_audio(destination, ffmpeg_executable):
                raise RuntimeError(f"输出验证失败: {destination}")
            logger.info("转换完成: %s -> %s", source, destination)
            result.succeeded += 1
            result.outputs.append(destination)
        except Exception as exc:
            logger.exception("转换失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
    return result
