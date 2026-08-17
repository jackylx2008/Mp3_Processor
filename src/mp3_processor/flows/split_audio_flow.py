"""批量切分音频工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.execution import (
    CancellationToken,
    ProgressCallback,
    TaskCancelled,
    check_cancelled,
    report_progress,
)
from mp3_processor.modules.audio_splitter import split_audio
from mp3_processor.modules.files import iter_files
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    input_extensions: list[str] | tuple[str, ...] | None = None,
    recursive: bool | None = None,
    duration_minutes: float | None = None,
    bitrate: str | None = None,
    ffmpeg_executable: str | None = None,
    overwrite: bool | None = None,
    max_files: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_token: CancellationToken | None = None,
) -> FlowResult:
    """发现音频并按固定时长切分到独立输出目录。"""
    config = context.flow_config("split_audio")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    target_root = context.resolve_path(output_dir or config.get("output_dir", "output/split"))
    extensions = input_extensions or config.get("input_extensions", ["mp3", "m4a"])
    use_recursive = bool(config.get("recursive", True)) if recursive is None else recursive
    use_overwrite = bool(config.get("overwrite", False)) if overwrite is None else overwrite
    segment_minutes = float(config.get("duration_minutes", 30)) if duration_minutes is None else duration_minutes
    target_bitrate = bitrate or str(config.get("bitrate", "192k"))
    ffmpeg = ffmpeg_executable or str(config.get("ffmpeg", context.config.get("app", {}).get("ffmpeg", "ffmpeg")))
    report_progress(progress, "scanning", f"正在扫描: {source_root}")
    files = list(iter_files(source_root, extensions, recursive=use_recursive))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    total = len(files)
    report_progress(progress, "running", f"发现 {total} 个待处理文件", total=total)
    for index, source in enumerate(files, start=1):
        check_cancelled(cancel_token)
        report_progress(progress, "running", f"正在分割: {source.name}", current=index - 1, total=total, item=source)
        relative_dir = source.parent.relative_to(source_root)
        destination_dir = target_root / relative_dir / source.stem
        try:
            outputs = split_audio(
                source,
                destination_dir,
                duration_minutes=segment_minutes,
                bitrate=target_bitrate,
                overwrite=use_overwrite,
                ffmpeg_executable=ffmpeg,
                cancel_token=cancel_token,
            )
            logger.info("切分完成: %s，共 %d 段", source, len(outputs))
            result.succeeded += 1
            result.outputs.extend(outputs)
        except FileExistsError as exc:
            logger.info("跳过已有输出: %s", exc)
            result.skipped += 1
        except TaskCancelled:
            raise
        except Exception as exc:
            logger.exception("切分失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
        report_progress(progress, "running", f"已处理: {source.name}", current=index, total=total, item=source)
    report_progress(progress, "completed", "音频分割完成", current=total, total=total)
    return result
