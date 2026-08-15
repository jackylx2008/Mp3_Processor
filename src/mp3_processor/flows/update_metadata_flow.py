"""批量更新音频元数据工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.execution import CancellationToken, ProgressCallback, check_cancelled, report_progress
from mp3_processor.modules.files import iter_files
from mp3_processor.modules.metadata_editor import album_for_file, title_from_filename, update_audio_tags
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    recursive: bool | None = None,
    artist: str | None = None,
    album: str | None = None,
    include_folder_in_album: bool | None = None,
    write: bool = False,
    max_files: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_token: CancellationToken | None = None,
) -> FlowResult:
    """为 MP3/M4A 设置标题、艺术家和专辑；默认预览。"""
    config = context.flow_config("update_metadata")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    use_recursive = bool(config.get("recursive", True)) if recursive is None else recursive
    report_progress(progress, "scanning", f"正在扫描: {source_root}")
    files = list(iter_files(source_root, ["mp3", "m4a"], recursive=use_recursive))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    target_artist = config.get("artist") if artist is None else artist
    base_album = config.get("album") if album is None else album
    include_folder = bool(config.get("include_folder_in_album", True)) if include_folder_in_album is None else include_folder_in_album
    total = len(files)
    report_progress(progress, "running", f"发现 {total} 个待处理文件", total=total)
    for index, source in enumerate(files, start=1):
        check_cancelled(cancel_token)
        report_progress(progress, "running", f"正在处理元数据: {source.name}", current=index - 1, total=total, item=source)
        target_album = album_for_file(
            source,
            source_root,
            base_album,
            include_folder,
        )
        if not write:
            logger.info("预览标签: %s | title=%s artist=%s album=%s", source, title_from_filename(source), target_artist, target_album)
            result.skipped += 1
            report_progress(progress, "running", f"已预览: {source.name}", current=index, total=total, item=source)
            continue
        try:
            update_audio_tags(source, artist=target_artist, album=target_album)
            logger.info("标签更新完成: %s", source)
            result.succeeded += 1
            result.outputs.append(source)
        except Exception as exc:
            logger.exception("标签更新失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
        report_progress(progress, "running", f"已处理: {source.name}", current=index, total=total, item=source)
    report_progress(progress, "completed", "元数据任务完成", current=total, total=total)
    return result
