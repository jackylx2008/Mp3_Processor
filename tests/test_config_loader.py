from pathlib import Path

from mp3_processor.config_loader import load_config


def test_load_config_expands_environment_and_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_INPUT", "sample/input")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'app:\n  input_path: "${TEST_INPUT}"\n  log_level: "${MISSING_LEVEL:-INFO}"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config["app"]["input_path"] == str(Path("sample/input"))
    assert config["app"]["log_level"] == "INFO"


def test_common_env_does_not_override_existing_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    (tmp_path / "common.env").write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
    config_file = tmp_path / "config.yaml"
    config_file.write_text('app:\n  log_level: "${LOG_LEVEL:-INFO}"\n', encoding="utf-8")

    config = load_config(config_file)

    assert config["app"]["log_level"] == "WARNING"


def test_empty_environment_default_remains_empty(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AUDIO_ARTIST", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text('metadata:\n  artist: "${AUDIO_ARTIST:-}"\n', encoding="utf-8")

    config = load_config(config_file)

    assert config["metadata"]["artist"] == ""
