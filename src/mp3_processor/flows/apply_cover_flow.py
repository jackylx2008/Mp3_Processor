"""批量写入音频封面工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.execution import CancellationToken, ProgressCallback, check_cancelled, report_progress
from mp3_processor.modules.cover_editor import embed_cover
from mp3_processor.modules.files import iter_files
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    cover_image: str | Path | None = None,
    recursive: bool | None = None,
    replace_existing: bool | None = None,
    write: bool = False,
    max_files: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_token: CancellationToken | None = None,
) -> FlowResult:
    """向 MP3/M4A/WMA 写入统一封面；默认预览。"""
    config = context.flow_config("apply_cover")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    cover = context.resolve_path(cover_image or config.get("cover_image", ""))
    if not cover.is_file():
        raise FileNotFoundError(f"封面图片不存在: {cover}")
    use_recursive = bool(config.get("recursive", True)) if recursive is None else recursive
    use_replace = bool(config.get("replace_existing", True)) if replace_existing is None else replace_existing
    report_progress(progress, "scanning", f"正在扫描: {source_root}")
    files = list(iter_files(source_root, ["mp3", "m4a", "wma"], recursive=use_recursive))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    total = len(files)
    report_progress(progress, "running", f"发现 {total} 个待处理文件", total=total)
    for index, source in enumerate(files, start=1):
        check_cancelled(cancel_token)
        report_progress(progress, "running", f"正在写入封面: {source.name}", current=index - 1, total=total, item=source)
        if not write:
            logger.info("预览封面写入: %s <- %s", source, cover)
            result.skipped += 1
            report_progress(progress, "running", f"已预览: {source.name}", current=index, total=total, item=source)
            continue
        try:
            embed_cover(source, cover, replace=use_replace)
            logger.info("封面写入完成: %s", source)
            result.succeeded += 1
            result.outputs.append(source)
        except Exception as exc:
            logger.exception("封面写入失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
        report_progress(progress, "running", f"已处理: {source.name}", current=index, total=total, item=source)
    report_progress(progress, "completed", "封面嵌入任务完成", current=total, total=total)
    return result
