"""封面图片裁剪、文字渲染和音频封面写入能力。"""

from __future__ import annotations

import struct
from pathlib import Path

from mutagen.asf import ASF
from mutagen.asf._attrs import ASFByteArrayAttribute
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image, ImageDraw, ImageFont


def crop_image(source: Path, destination: Path, crop_box: tuple[int, int, int, int]) -> Path:
    """裁剪图片并保留适合目标扩展名的色彩模式。"""
    if not source.is_file():
        raise FileNotFoundError(f"图片不存在: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        cropped = image.crop(crop_box)
        if destination.suffix.lower() in {".jpg", ".jpeg"} and cropped.mode not in {"RGB", "L"}:
            cropped = cropped.convert("RGB")
        cropped.save(destination)
    return destination


def render_text(
    source: Path,
    destination: Path,
    lines: list[str],
    *,
    font_path: Path,
    font_size: int = 64,
    color: tuple[int, int, int] = (255, 255, 255),
    top_ratio: float = 0.75,
    line_spacing: int = 12,
) -> Path:
    """在图片下半区域居中绘制多行文字。"""
    with Image.open(source) as image:
        canvas = image.convert("RGBA")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(str(font_path), font_size)
        y = int(canvas.height * top_ratio)
        for line in (line for line in lines if line):
            box = draw.textbbox((0, 0), line, font=font)
            width, height = box[2] - box[0], box[3] - box[1]
            draw.text(((canvas.width - width) / 2, y), line, font=font, fill=(*color, 255))
            y += height + line_spacing
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.suffix.lower() in {".jpg", ".jpeg"}:
            canvas.convert("RGB").save(destination)
        else:
            canvas.save(destination)
    return destination


def embed_cover(audio_path: Path, cover_path: Path, *, replace: bool = True) -> None:
    """向 MP3、M4A 或 WMA 文件写入封面。"""
    image_data = cover_path.read_bytes()
    mime = _image_mime(cover_path)
    suffix = audio_path.suffix.lower()
    if suffix == ".mp3":
        audio = MP3(audio_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
        if tags is None:
            raise RuntimeError(f"无法创建 MP3 ID3 标签: {audio_path}")
        if replace:
            tags.delall("APIC")
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=image_data))
        audio.save()
        return
    if suffix == ".m4a":
        audio = MP4(audio_path)
        image_format = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
        audio["covr"] = [MP4Cover(image_data, imageformat=image_format)]
        audio.save()
        return
    if suffix == ".wma":
        audio = ASF(audio_path)
        picture = (
            struct.pack("<bi", 3, len(image_data))
            + mime.encode("utf-16-le")
            + b"\x00\x00"
            + "Cover".encode("utf-16-le")
            + b"\x00\x00"
            + image_data
        )
        audio["WM/Picture"] = [ASFByteArrayAttribute(picture)]
        audio.save()
        return
    raise ValueError(f"不支持写入封面的格式: {audio_path.suffix}")


def _image_mime(path: Path) -> str:
    if path.suffix.lower() == ".png":
        return "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return "image/jpeg"
    raise ValueError("音频封面仅支持 PNG 或 JPEG")
