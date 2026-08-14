from pathlib import Path

from mp3_processor.modules import audio_splitter


def test_split_audio_uses_configured_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.mp3"
    source.write_bytes(b"audio")
    converter = tmp_path / "ffmpeg-custom"
    calls: list[object] = []

    class FakeSegment:
        converter = ""

        @classmethod
        def from_file(cls, path: Path):
            calls.append(path)
            return cls()

        def __len__(self) -> int:
            return 0

    monkeypatch.setattr(audio_splitter, "AudioSegment", FakeSegment)
    monkeypatch.setattr(audio_splitter, "require_ffmpeg", lambda value: str(converter))

    outputs = audio_splitter.split_audio(
        source,
        tmp_path / "output",
        duration_minutes=1,
        ffmpeg_executable=str(converter),
    )

    assert outputs == []
    assert FakeSegment.converter == str(converter)
    assert calls == [source]
