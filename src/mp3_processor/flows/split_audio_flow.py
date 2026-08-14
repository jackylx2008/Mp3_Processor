"""批量切分音频工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.modules.audio_splitter import split_audio
from mp3_processor.modules.files import iter_files
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_files: int | None = None,
) -> FlowResult:
    """发现音频并按固定时长切分到独立输出目录。"""
    config = context.flow_config("split_audio")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    target_root = context.resolve_path(output_dir or config.get("output_dir", "output/split"))
    files = list(iter_files(source_root, config.get("input_extensions", ["mp3", "m4a"]), recursive=bool(config.get("recursive", True))))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    for source in files:
        relative_dir = source.parent.relative_to(source_root)
        destination_dir = target_root / relative_dir / source.stem
        try:
            outputs = split_audio(
                source,
                destination_dir,
                duration_minutes=float(config.get("duration_minutes", 30)),
                bitrate=str(config.get("bitrate", "192k")),
                overwrite=bool(config.get("overwrite", False)),
                ffmpeg_executable=str(config.get("ffmpeg", "ffmpeg")),
            )
            logger.info("切分完成: %s，共 %d 段", source, len(outputs))
            result.succeeded += 1
            result.outputs.extend(outputs)
        except FileExistsError as exc:
            logger.info("跳过已有输出: %s", exc)
            result.skipped += 1
        except Exception as exc:
            logger.exception("切分失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
    return result
