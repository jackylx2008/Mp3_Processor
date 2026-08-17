"""批量转换音频工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.execution import CancellationToken, ProgressCallback, check_cancelled, report_progress
from mp3_processor.modules.audio_converter import OUTPUT_CODECS, convert_audio, validate_audio
from mp3_processor.modules.files import iter_files, output_path_for
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    input_extensions: list[str] | tuple[str, ...] | None = None,
    output_type: str | None = None,
    recursive: bool | None = None,
    max_depth: int | None = None,
    bitrate: str | None = None,
    ffmpeg_executable: str | None = None,
    overwrite: bool | None = None,
    validate_output: bool | None = None,
    max_files: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_token: CancellationToken | None = None,
) -> FlowResult:
    """发现源文件、转换为指定格式并验证输出。"""
    config = context.flow_config("convert_audio")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    target_root = context.resolve_path(output_dir or config.get("output_dir", "output/converted"))
    extensions = input_extensions or config.get("input_extensions", ["mp3", "m4a", "mp4", "wma"])
    target_type = (output_type or str(config.get("output_type", "mp3"))).lower().lstrip(".")
    if target_type not in OUTPUT_CODECS:
        raise ValueError(f"不支持的输出类型: {target_type}；可选: {', '.join(OUTPUT_CODECS)}")
    use_recursive = bool(config.get("recursive", True)) if recursive is None else recursive
    depth = int(config.get("max_depth", 0)) if max_depth is None else max_depth
    report_progress(progress, "scanning", f"正在扫描: {source_root}")
    files = list(
        iter_files(
            source_root,
            extensions,
            recursive=use_recursive,
            max_depth=depth,
        )
    )
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]

    result = FlowResult(discovered=len(files))
    ffmpeg = ffmpeg_executable or str(config.get("ffmpeg", context.config.get("app", {}).get("ffmpeg", "ffmpeg")))
    use_overwrite = bool(config.get("overwrite", False)) if overwrite is None else overwrite
    use_validation = bool(config.get("validate_output", True)) if validate_output is None else validate_output
    target_bitrate = bitrate or str(config.get("bitrate", "192k"))
    total = len(files)
    report_progress(progress, "running", f"发现 {total} 个待处理文件", total=total)
    for index, source in enumerate(files, start=1):
        check_cancelled(cancel_token)
        report_progress(progress, "running", f"正在转换: {source.name}", current=index - 1, total=total, item=source)
        destination = output_path_for(source, source_root, target_root, f".{target_type}")
        if destination.exists() and not use_overwrite:
            logger.info("跳过已存在文件: %s", destination)
            result.skipped += 1
            report_progress(progress, "running", f"已跳过: {source.name}", current=index, total=total, item=source)
            continue
        try:
            convert_audio(
                source,
                destination,
                bitrate=target_bitrate,
                overwrite=use_overwrite,
                ffmpeg_executable=ffmpeg,
            )
            if use_validation and not validate_audio(destination, ffmpeg):
                raise RuntimeError(f"输出验证失败: {destination}")
            logger.info("转换完成: %s -> %s", source, destination)
            result.succeeded += 1
            result.outputs.append(destination)
        except Exception as exc:
            logger.exception("转换失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
        report_progress(progress, "running", f"已处理: {source.name}", current=index, total=total, item=source)
    report_progress(progress, "completed", "音频转换完成", current=total, total=total)
    return result
