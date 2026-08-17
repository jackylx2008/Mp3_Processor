from pathlib import Path
from subprocess import CompletedProcess

import pytest

from mp3_processor.modules import audio_converter


@pytest.mark.parametrize(
    ("suffix", "codec", "uses_bitrate"),
    [
        (".mp3", "libmp3lame", True),
        (".m4a", "aac", True),
        (".wma", "wmav2", True),
        (".wav", "pcm_s16le", False),
        (".flac", "flac", False),
        (".ogg", "libvorbis", True),
    ],
)
def test_convert_audio_selects_codec_from_output_type(
    tmp_path: Path,
    monkeypatch,
    suffix: str,
    codec: str,
    uses_bitrate: bool,
) -> None:
    source = tmp_path / "source.mp3"
    source.write_bytes(b"audio")
    destination = tmp_path / f"output{suffix}"
    commands: list[list[str]] = []
    monkeypatch.setattr(audio_converter, "require_ffmpeg", lambda value: "ffmpeg")
    monkeypatch.setattr(
        audio_converter.subprocess,
        "run",
        lambda command, **kwargs: commands.append(command) or CompletedProcess(command, 0, "", ""),
    )

    audio_converter.convert_audio(source, destination, bitrate="256k")

    codec_index = commands[0].index("-codec:a")
    assert commands[0][codec_index : codec_index + 2] == ["-codec:a", codec]
    assert ("-b:a" in commands[0]) is uses_bitrate


def test_convert_audio_rejects_unknown_output_type(tmp_path: Path) -> None:
    source = tmp_path / "source.mp3"
    source.write_bytes(b"audio")

    with pytest.raises(ValueError, match="不支持的输出类型"):
        audio_converter.convert_audio(source, tmp_path / "output.xyz")
