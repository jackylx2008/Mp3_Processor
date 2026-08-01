"""批量写入音频封面工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.modules.cover_editor import embed_cover
from mp3_processor.modules.files import iter_files
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    cover_image: str | Path | None = None,
    write: bool = False,
    max_files: int | None = None,
) -> FlowResult:
    """向 MP3/M4A/WMA 写入统一封面；默认预览。"""
    config = context.flow_config("apply_cover")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    cover = context.resolve_path(cover_image or config.get("cover_image", ""))
    if not cover.is_file():
        raise FileNotFoundError(f"封面图片不存在: {cover}")
    files = list(iter_files(source_root, ["mp3", "m4a", "wma"], recursive=bool(config.get("recursive", True))))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    for source in files:
        if not write:
            logger.info("预览封面写入: %s <- %s", source, cover)
            result.skipped += 1
            continue
        try:
            embed_cover(source, cover, replace=bool(config.get("replace_existing", True)))
            logger.info("封面写入完成: %s", source)
            result.succeeded += 1
            result.outputs.append(source)
        except Exception as exc:
            logger.exception("封面写入失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
    return result
