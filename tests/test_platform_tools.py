import logging
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from mp3_processor.context import AppContext
from mp3_processor.platform_tools import resolve_executable


def test_resolve_executable_accepts_explicit_unicode_path(tmp_path: Path) -> None:
    executable = tmp_path / "工具" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    executable.parent.mkdir()
    executable.write_bytes(b"")
    if os.name != "nt":
        executable.chmod(0o755)

    assert Path(resolve_executable(executable, name="FFmpeg")) == executable.resolve()


def test_resolve_executable_reports_missing_command() -> None:
    with pytest.raises(FileNotFoundError, match="找不到 FFmpeg"):
        resolve_executable("definitely-missing-ffmpeg-command", name="FFmpeg")


def test_pure_paths_preserve_foreign_platform_syntax() -> None:
    assert PureWindowsPath(r"C:\音频\专辑\track.m4a").parts[-2:] == ("专辑", "track.m4a")
    assert PurePosixPath("/音频/专辑/track.m4a").parts[-2:] == ("专辑", "track.m4a")


def test_context_resolves_relative_and_user_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path / "用户"))
    context = AppContext(tmp_path, {}, logging.getLogger("test"))

    assert context.resolve_path("相对/音频.mp3") == tmp_path / "相对" / "音频.mp3"
    assert context.resolve_path("~/音频.mp3") == Path("~/音频.mp3").expanduser()
