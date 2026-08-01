from pathlib import Path

from mp3_processor.modules.metadata_editor import album_for_file, title_from_filename


def test_title_from_filename_removes_episode_leading_zeroes() -> None:
    assert title_from_filename(Path("故事第001集.m4a")) == "故事第1集"


def test_album_for_file_appends_parent_directory(tmp_path: Path) -> None:
    root = tmp_path / "input"
    audio = root / "season-1" / "track.m4a"

    assert album_for_file(audio, root, "Demo", True) == "Demo season-1"
    assert album_for_file(audio, root, "Demo", False) == "Demo"
