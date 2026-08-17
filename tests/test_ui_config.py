from pathlib import Path

from mp3_processor.config_loader import load_config


def test_ui_config_contains_all_workflows() -> None:
    project_root = Path(__file__).resolve().parents[1]

    config = load_config(project_root / "ui_config.yaml")

    assert set(config["workflows"]) == {
        "convert_audio",
        "update_metadata",
        "prepare_cover",
        "apply_cover",
        "split_audio",
    }
    assert config["app"]["ffmpeg"]
    assert config["workflows"]["convert_audio"]["workers"] == "8"
