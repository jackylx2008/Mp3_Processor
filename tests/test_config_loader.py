import os
from pathlib import Path

import pytest

from mp3_processor import config_loader
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


@pytest.mark.parametrize(
    ("system", "variable", "root"),
    [
        ("Windows", "CLOUDSTATION_ROOT_WINDOWS", r"E:\SynologyCustom"),
        ("Darwin", "CLOUDSTATION_ROOT_MACOS", "/Volumes/SynologyCustom"),
        ("Linux", "CLOUDSTATION_ROOT_LINUX", "/mnt/synology-custom"),
    ],
)
def test_cloudstation_root_selects_current_platform(
    tmp_path: Path,
    monkeypatch,
    system: str,
    variable: str,
    root: str,
) -> None:
    for name in (
        "CLOUDSTATION_ROOT",
        "CLOUDSTATION_ROOT_WINDOWS",
        "CLOUDSTATION_ROOT_MACOS",
        "CLOUDSTATION_ROOT_DARWIN",
        "CLOUDSTATION_ROOT_LINUX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(variable, root)
    monkeypatch.setattr(config_loader.platform, "system", lambda: system)
    config_file = tmp_path / "config.yaml"
    config_file.write_text('app:\n  cloudstation_root: "${CLOUDSTATION_ROOT}"\n', encoding="utf-8")

    config = load_config(config_file)

    assert config["app"]["cloudstation_root"] == str(Path(root).expanduser())


@pytest.mark.parametrize(
    ("system", "root"),
    [
        ("Windows", r"D:\CloudStaion"),
        ("Darwin", "~/SynologyDrive"),
        ("Linux", "~/CloudStation"),
    ],
)
def test_cloudstation_root_has_platform_default(
    tmp_path: Path,
    monkeypatch,
    system: str,
    root: str,
) -> None:
    for name in (
        "CLOUDSTATION_ROOT",
        "CLOUDSTATION_ROOT_WINDOWS",
        "CLOUDSTATION_ROOT_MACOS",
        "CLOUDSTATION_ROOT_DARWIN",
        "CLOUDSTATION_ROOT_LINUX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config_loader.platform, "system", lambda: system)
    config_file = tmp_path / "config.yaml"
    config_file.write_text('app:\n  cloudstation_root: "${CLOUDSTATION_ROOT}"\n', encoding="utf-8")

    config = load_config(config_file)

    assert config["app"]["cloudstation_root"] == str(Path(root).expanduser())


def test_explicit_cloudstation_root_has_highest_priority(tmp_path: Path, monkeypatch) -> None:
    explicit_root = tmp_path / "同步目录"
    monkeypatch.setenv("CLOUDSTATION_ROOT", str(explicit_root))
    monkeypatch.setenv("CLOUDSTATION_ROOT_MACOS", "~/SynologyDrive")
    monkeypatch.setattr(config_loader.platform, "system", lambda: "Darwin")
    config_file = tmp_path / "config.yaml"
    config_file.write_text('app:\n  cloudstation_root: "${CLOUDSTATION_ROOT}"\n', encoding="utf-8")

    config = load_config(config_file)

    assert config["app"]["cloudstation_root"] == str(explicit_root)
    assert os.environ["CLOUDSTATION_ROOT"] == str(explicit_root)
