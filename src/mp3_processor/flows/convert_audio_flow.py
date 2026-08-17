"""批量转换音频工作流。"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from logging_config import get_logger
from mp3_processor.context import AppContext
from mp3_processor.execution import CancellationToken, ProgressCallback, check_cancelled, report_progress
from mp3_processor.modules.audio_converter import OUTPUT_CODECS, convert_audio, validate_audio
from mp3_processor.modules.files import iter_files, output_path_for
from mp3_processor.results import FlowResult


logger = get_logger(__name__)
ConversionStatus = Literal["succeeded", "skipped", "failed"]
MAX_CONVERSION_WORKERS = 32


@dataclass(frozen=True)
class ConversionJob:
    source: Path
    destination: Path


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
    workers: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_token: CancellationToken | None = None,
) -> FlowResult:
    """发现源文件，并发转换为指定格式并验证输出。"""
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
    worker_count = workers if workers is not None else int(config.get("workers", 8))
    if not 1 <= worker_count <= MAX_CONVERSION_WORKERS:
        raise ValueError(f"workers 必须在 1 到 {MAX_CONVERSION_WORKERS} 之间")

    total = len(files)
    report_progress(
        progress,
        "running",
        f"发现 {total} 个待处理文件，并发数 {worker_count}",
        total=total,
    )
    _run_concurrently(
        files,
        source_root=source_root,
        target_root=target_root,
        target_type=target_type,
        worker_count=worker_count,
        bitrate=target_bitrate,
        overwrite=use_overwrite,
        validate_output=use_validation,
        ffmpeg=ffmpeg,
        result=result,
        progress=progress,
        cancel_token=cancel_token,
    )
    result.outputs.sort(key=lambda path: str(path).casefold())
    report_progress(progress, "completed", "音频转换完成", current=total, total=total)
    return result


def _run_concurrently(
    files: list[Path],
    *,
    source_root: Path,
    target_root: Path,
    target_type: str,
    worker_count: int,
    bitrate: str,
    overwrite: bool,
    validate_output: bool,
    ffmpeg: str,
    result: FlowResult,
    progress: ProgressCallback | None,
    cancel_token: CancellationToken | None,
) -> None:
    jobs, processed = _prepare_jobs(
        files,
        source_root=source_root,
        target_root=target_root,
        target_type=target_type,
        result=result,
        progress=progress,
    )
    if not jobs:
        check_cancelled(cancel_token)
        return

    executor = ThreadPoolExecutor(max_workers=min(worker_count, len(jobs)), thread_name_prefix="audio-convert")
    pending: dict[Future[tuple[ConversionStatus, str | None]], ConversionJob] = {}
    job_iterator = iter(jobs)
    cancellation_requested = False

    def submit_next() -> bool:
        nonlocal cancellation_requested
        if cancel_token is not None and cancel_token.cancelled:
            cancellation_requested = True
            return False
        try:
            job = next(job_iterator)
        except StopIteration:
            return False
        future = executor.submit(
            _convert_one,
            job,
            bitrate=bitrate,
            overwrite=overwrite,
            validate_output=validate_output,
            ffmpeg=ffmpeg,
        )
        pending[future] = job
        return True

    try:
        check_cancelled(cancel_token)
        for _ in range(min(worker_count, len(jobs))):
            submit_next()

        while pending:
            completed, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in completed:
                job = pending.pop(future)
                status, error = future.result()
                _record_result(result, status, job.destination, error)
                processed += 1
                report_progress(
                    progress,
                    "running",
                    _progress_message(status, job.source.name),
                    current=processed,
                    total=len(files),
                    item=job.source,
                )
                if cancel_token is not None and cancel_token.cancelled:
                    cancellation_requested = True
                if not cancellation_requested:
                    submit_next()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    check_cancelled(cancel_token)


def _prepare_jobs(
    files: list[Path],
    *,
    source_root: Path,
    target_root: Path,
    target_type: str,
    result: FlowResult,
    progress: ProgressCallback | None,
) -> tuple[list[ConversionJob], int]:
    jobs: list[ConversionJob] = []
    destinations: dict[Path, Path] = {}
    processed = 0
    source_paths = {source.resolve(): source for source in files}

    for source in files:
        destination = output_path_for(source, source_root, target_root, f".{target_type}")
        resolved_destination = destination.resolve(strict=False)
        if input_owner := source_paths.get(resolved_destination):
            if input_owner == source:
                message = f"输入和输出不能是同一文件: {source}"
            else:
                message = f"输出路径与输入文件冲突: {source} -> {input_owner}"
            logger.error(message)
            result.failed += 1
            result.errors.append(message)
            processed += 1
            report_progress(
                progress,
                "running",
                f"转换失败: {source.name}",
                current=processed,
                total=len(files),
                item=source,
            )
            continue
        if owner := destinations.get(resolved_destination):
            logger.warning("跳过目标冲突: %s 与 %s -> %s", owner, source, destination)
            result.skipped += 1
            processed += 1
            report_progress(
                progress,
                "running",
                f"目标冲突，已跳过: {source.name}",
                current=processed,
                total=len(files),
                item=source,
            )
            continue
        destinations[resolved_destination] = source
        jobs.append(ConversionJob(source, destination))
    return jobs, processed


def _convert_one(
    job: ConversionJob,
    *,
    bitrate: str,
    overwrite: bool,
    validate_output: bool,
    ffmpeg: str,
) -> tuple[ConversionStatus, str | None]:
    if job.destination.exists() and not overwrite:
        logger.info("跳过已存在文件: %s", job.destination)
        return "skipped", None
    try:
        convert_audio(
            job.source,
            job.destination,
            bitrate=bitrate,
            overwrite=overwrite,
            ffmpeg_executable=ffmpeg,
        )
        if validate_output and not validate_audio(job.destination, ffmpeg):
            raise RuntimeError(f"输出验证失败: {job.destination}")
        logger.info("转换完成: %s -> %s", job.source, job.destination)
        return "succeeded", None
    except Exception as exc:
        logger.exception("转换失败: %s", job.source)
        return "failed", str(exc)


def _record_result(
    result: FlowResult,
    status: ConversionStatus,
    destination: Path,
    error: str | None,
) -> None:
    if status == "succeeded":
        result.succeeded += 1
        result.outputs.append(destination)
    elif status == "skipped":
        result.skipped += 1
    else:
        result.failed += 1
        result.errors.append(error or f"转换失败: {destination}")


def _progress_message(status: ConversionStatus, name: str) -> str:
    messages = {
        "succeeded": "转换完成",
        "skipped": "已跳过",
        "failed": "转换失败",
    }
    return f"{messages[status]}: {name}"
