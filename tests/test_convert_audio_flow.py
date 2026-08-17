import logging
from pathlib import Path
from threading import Barrier, Lock

import pytest

from mp3_processor.context import AppContext
from mp3_processor.flows import convert_audio_flow


def _context(source_root: Path, output_root: Path, **flow_config: object) -> AppContext:
    config = {
        "input_path": str(source_root),
        "output_dir": str(output_root),
        "input_extensions": ["mp3"],
        "output_type": "flac",
        **flow_config,
    }
    return AppContext(
        source_root.parent,
        {
            "app": {"input_path": str(source_root)},
            "flows": {"convert_audio": config},
        },
        logging.getLogger("test"),
    )


def test_flow_discovers_mp3_and_uses_selected_output_type(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    source = source_root / "专辑" / "track.mp3"
    source.parent.mkdir()
    source.write_bytes(b"audio")
    output_root = tmp_path / "output"
    context = _context(source_root, output_root)

    def fake_convert(source_path: Path, destination: Path, **kwargs) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"converted")
        return destination

    monkeypatch.setattr(convert_audio_flow, "convert_audio", fake_convert)
    monkeypatch.setattr(convert_audio_flow, "validate_audio", lambda path, executable: True)

    result = convert_audio_flow.run(context)

    assert result.discovered == 1
    assert result.succeeded == 1
    assert result.outputs == [output_root / "专辑" / "track.flac"]


def test_flow_runs_multiple_ffmpeg_jobs_concurrently(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    for index in range(4):
        (source_root / f"track-{index}.mp3").write_bytes(b"audio")
    context = _context(source_root, tmp_path / "output", workers=3, validate_output=False)
    barrier = Barrier(3)
    lock = Lock()
    active = 0
    maximum_active = 0
    started = 0

    def fake_convert(source_path: Path, destination: Path, **kwargs) -> Path:
        nonlocal active, maximum_active, started
        with lock:
            active += 1
            started += 1
            batch_index = started
            maximum_active = max(maximum_active, active)
        try:
            if batch_index <= 3:
                barrier.wait(timeout=2)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"converted")
            return destination
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(convert_audio_flow, "convert_audio", fake_convert)

    result = convert_audio_flow.run(context)

    assert result.succeeded == 4
    assert maximum_active == 3


def test_flow_skips_sources_that_map_to_the_same_destination(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    (source_root / "track.m4a").write_bytes(b"m4a")
    (source_root / "track.mp3").write_bytes(b"mp3")
    context = _context(
        source_root,
        tmp_path / "output",
        input_extensions=["m4a", "mp3"],
        output_type="mp3",
        validate_output=False,
    )

    def fake_convert(source_path: Path, destination: Path, **kwargs) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"converted")
        return destination

    monkeypatch.setattr(convert_audio_flow, "convert_audio", fake_convert)

    result = convert_audio_flow.run(context)

    assert result.discovered == 2
    assert result.succeeded == 1
    assert result.skipped == 1


@pytest.mark.parametrize("workers", [0, 33])
def test_flow_rejects_unsafe_worker_counts(tmp_path: Path, workers: int) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    context = _context(source_root, tmp_path / "output")

    with pytest.raises(ValueError, match="workers 必须在 1 到 32 之间"):
        convert_audio_flow.run(context, workers=workers)


def test_flow_never_overwrites_another_source_file(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    (source_root / "track.m4a").write_bytes(b"m4a")
    (source_root / "track.mp3").write_bytes(b"mp3")
    context = _context(
        source_root,
        source_root,
        input_extensions=["m4a", "mp3"],
        output_type="mp3",
        overwrite=True,
        validate_output=False,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("存在源文件路径冲突时不应启动转换")

    monkeypatch.setattr(convert_audio_flow, "convert_audio", fail_if_called)

    result = convert_audio_flow.run(context)

    assert result.discovered == 2
    assert result.failed == 2
    assert all("输入" in error for error in result.errors)
