from pathlib import Path

from PIL import Image

from mp3_processor.modules.cover_editor import crop_image


def test_crop_image_writes_expected_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "output" / "cropped.png"
    Image.new("RGBA", (100, 80), (255, 0, 0, 128)).save(source)

    crop_image(source, destination, (10, 10, 70, 60))

    with Image.open(destination) as image:
        assert image.size == (60, 50)
        assert image.mode == "RGBA"
