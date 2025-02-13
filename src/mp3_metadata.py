import logging
import os
import sys

import eyed3
import yaml

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.logging_config import setup_logger  # 引入日志配置函数

# 初始化日志记录器，日志文件为 test_mp3_output.log
logger = setup_logger(log_level=logging.INFO, log_file="./logs/mp3_metadata.log")


# 读取 YAML 配置文件
def read_yaml(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error("读取 YAML 文件失败: %s", e)
        return None


# 修改 MP3 文件的标签
def modify_mp3_tags(mp3_file, artist=None, album=None):
    try:
        # 提取文件名作为 title
        title = os.path.splitext(os.path.basename(mp3_file))[0]

        # 加载 MP3 文件
        audiofile = eyed3.load(mp3_file)

        # 设置标题为文件名
        audiofile.tag.title = title
        logger.info("修改标题为: %s", title)

        if artist:
            audiofile.tag.artist = artist
            logger.info("修改艺术家为: %s", artist)

        if album:
            audiofile.tag.album = album
            logger.info("修改专辑为: %s", album)

        # 保存修改
        audiofile.tag.save()
        logger.info("MP3 文件标签已保存: %s", mp3_file)
    except Exception as e:
        logger.error("修改 MP3 标签失败: %s", e)


# 遍历文件夹下所有 MP3 文件并修改标签
def process_mp3_files(directory, artist=None, album=None):
    try:
        # 遍历文件夹中的所有文件
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".mp3"):
                    mp3_file = os.path.join(root, file)
                    logger.info("正在处理文件: %s", mp3_file)
                    modify_mp3_tags(mp3_file, artist, album)
    except Exception as e:
        logger.error("遍历文件夹失败: %s", e)


# 主程序
def main():
    # 读取配置文件
    config = read_yaml("./mp3_metadata.yaml")

    if config:
        mp3_directory = "./mp3_files/output"
        artist = config.get("artist")
        album = config.get("album")

        if mp3_directory:
            # 处理文件夹中的所有 MP3 文件
            process_mp3_files(mp3_directory, artist, album)
        else:
            logger.error("配置文件中未找到 mp3_directory")
    else:
        logger.error("未能读取配置文件")


if __name__ == "__main__":
    main()
