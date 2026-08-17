import logging
from pathlib import Path

from mp3_processor.context import AppContext
from mp3_processor.flows import convert_audio_flow


def test_flow_discovers_mp3_and_uses_selected_output_type(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    source = source_root / "专辑" / "track.mp3"
    source.parent.mkdir()
    source.write_bytes(b"audio")
    output_root = tmp_path / "output"
    context = AppContext(
        tmp_path,
        {
            "app": {"input_path": str(source_root)},
            "flows": {
                "convert_audio": {
                    "input_path": str(source_root),
                    "output_dir": str(output_root),
                    "input_extensions": ["mp3"],
                    "output_type": "flac",
                }
            },
        },
        logging.getLogger("test"),
    )

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
