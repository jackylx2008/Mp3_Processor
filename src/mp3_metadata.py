import logging
import os
import re
import sys

import yaml
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.logging_config import setup_logger  # 引入日志配置函数

# 初始化日志记录器
logger = setup_logger(log_level=logging.INFO, log_file="./logs/audio_metadata.log")


def read_yaml(file_path):
    """读取 YAML 配置文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error("读取 YAML 文件失败: %s", e)
        return None


def modify_audio_tags(audio_file, artist=None, album=None):
    """修改 MP3 或 M4A 文件的元数据"""
    try:
        title = os.path.splitext(os.path.basename(audio_file))[0]  # 以文件名作为标题
        title = re.sub(r"(第)0+(\d+)(集)", r"\1\2\3", title)  # 去零

        if audio_file.endswith(".mp3"):
            audio = EasyID3(audio_file)
            audio["title"] = title
            if artist:
                audio["artist"] = artist
            if album:
                audio["album"] = album
        elif audio_file.endswith(".m4a"):
            audio = MP4(audio_file)
            audio["\xa9nam"] = [title]
            if artist:
                audio["\xa9ART"] = [artist]
            if album:
                audio["\xa9alb"] = [album]
        else:
            logger.warning("不支持的文件格式: %s", audio_file)
            return

        audio.save()
        logger.info("标签已保存: %s", audio_file)
    except Exception as e:
        logger.error("修改标签失败: %s", e)


def process_audio_files(directory, artist=None, album=None):
    """遍历文件夹并修改 MP3 和 M4A 文件的元数据"""
    if not os.path.exists(directory):
        logger.error("目录不存在: %s", directory)
        return

    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".mp3", ".m4a")):
                    audio_file = os.path.join(root, file)
                    logger.info("正在处理文件: %s", audio_file)
                    modify_audio_tags(audio_file, artist, album)
    except Exception as e:
        logger.error("遍历文件夹失败: %s", e)


if __name__ == "__main__":
    config = read_yaml("./mp3_metadata.yaml")

    if config:
        audio_directory = f"C:/Users/bcjt_/OneDrive/Desktop/《纳尼亚传奇》"
        artist = config.get("artist")
        album = config.get(f"album")

        if audio_directory:
            process_audio_files(audio_directory, artist, album)
        else:
            logger.error("配置文件中未找到 audio_directory")
    else:
        logger.error("未能读取配置文件")
