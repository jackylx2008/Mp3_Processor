"""批量裁剪封面图片工作流。"""

from __future__ import annotations

from pathlib import Path

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.modules.cover_editor import crop_image
from mp3_processor.modules.files import IMAGE_EXTENSIONS, iter_files, output_path_for
from mp3_processor.results import FlowResult


logger = get_logger(__name__)


def run(
    context: AppContext,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_files: int | None = None,
) -> FlowResult:
    """发现图片并按配置的矩形区域批量裁剪。"""
    config = context.flow_config("prepare_cover")
    source_root = context.resolve_path(input_path or config.get("input_path", "assets/cover_images/input"))
    target_root = context.resolve_path(output_dir or config.get("output_dir", "output/covers"))
    crop_values = config.get("crop_box", [0, 0, 1000, 1000])
    if not isinstance(crop_values, list) or len(crop_values) != 4:
        raise ValueError("flows.prepare_cover.crop_box 必须包含四个整数")
    crop_box = (
        int(crop_values[0]),
        int(crop_values[1]),
        int(crop_values[2]),
        int(crop_values[3]),
    )
    files = list(iter_files(source_root, IMAGE_EXTENSIONS, recursive=bool(config.get("recursive", True))))
    limit = max_files if max_files is not None else int(config.get("max_files", 0))
    if limit > 0:
        files = files[:limit]
    result = FlowResult(discovered=len(files))
    for source in files:
        destination = output_path_for(source, source_root, target_root, source.suffix.lower())
        if destination.exists() and not bool(config.get("overwrite", False)):
            result.skipped += 1
            continue
        try:
            crop_image(source, destination, crop_box)
            logger.info("封面裁剪完成: %s -> %s", source, destination)
            result.succeeded += 1
            result.outputs.append(destination)
        except Exception as exc:
            logger.exception("封面裁剪失败: %s", source)
            result.failed += 1
            result.errors.append(str(exc))
    return result
