"""批量更新音频元数据工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.modules.files import iter_files
from mp3_processor.modules.metadata_editor import album_for_file, title_from_filename, update_audio_tags
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    write: bool = False,
    max_files: int | None = None,
) -> FlowResult:
    """为 MP3/M4A 设置标题、艺术家和专辑；默认预览。"""
    config = context.flow_config("update_metadata")
    source_root = context.resolve_path(input_path or config.get("input_path", context.config["app"]["input_path"]))
    files = list(iter_files(source_root, ["mp3", "m4a"], recursive=bool(config.get("recursive", True))))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    for source in files:
        album = album_for_file(
            source,
            source_root,
            config.get("album"),
            bool(config.get("include_folder_in_album", True)),
        )
        if not write:
            logger.info("预览标签: %s | title=%s artist=%s album=%s", source, title_from_filename(source), config.get("artist"), album)
            result.skipped += 1
            continue
        try:
            update_audio_tags(source, artist=config.get("artist"), album=album)
            logger.info("标签更新完成: %s", source)
            result.succeeded += 1
            result.outputs.append(source)
        except Exception as exc:
            logger.exception("标签更新失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
    return result
