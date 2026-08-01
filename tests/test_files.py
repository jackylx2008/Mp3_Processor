from pathlib import Path

from mp3_processor.modules.files import iter_files, output_path_for


def test_iter_files_is_recursive_filtered_and_stable(tmp_path: Path) -> None:
    (tmp_path / "b.m4a").write_bytes(b"")
    (tmp_path / "a.txt").write_bytes(b"")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.M4A").write_bytes(b"")

    files = list(iter_files(tmp_path, ["m4a"]))

    assert files == [tmp_path / "b.m4a", nested / "a.M4A"]


def test_output_path_preserves_relative_tree(tmp_path: Path) -> None:
    source_root = tmp_path / "input"
    source = source_root / "album" / "track.m4a"
    output_root = tmp_path / "output"

    assert output_path_for(source, source_root, output_root, ".mp3") == output_root / "album" / "track.mp3"


def test_iter_files_can_limit_recursion_depth(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = first / "second"
    second.mkdir(parents=True)
    (first / "one.m4a").write_bytes(b"")
    (second / "two.m4a").write_bytes(b"")

    assert list(iter_files(tmp_path, ["m4a"], max_depth=1)) == [first / "one.m4a"]
