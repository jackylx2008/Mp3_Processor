from pathlib import Path

from PIL import Image


def test_app_icon_assets_cover_both_desktop_platforms() -> None:
    icon_root = Path(__file__).resolve().parents[1] / "assets" / "app_icon"

    with Image.open(icon_root / "mp3_processor.png") as png:
        assert png.format == "PNG"
        assert png.size == (512, 512)

    with Image.open(icon_root / "mp3_processor.ico") as ico:
        assert ico.format == "ICO"
        assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= ico.info["sizes"]

    with Image.open(icon_root / "mp3_processor.icns") as icns:
        assert icns.format == "ICNS"
        assert icns.size == (1024, 1024)
