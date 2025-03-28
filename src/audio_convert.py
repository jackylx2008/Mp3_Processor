import logging
import os
import sys

import ffmpeg
import yaml

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.logging_config import setup_logger  # 引入日志配置函数

# 初始化日志记录器，日志文件为 test_mp3_output.log
logger = setup_logger(log_level=logging.INFO, log_file="./logs/audio_convert.log")


# 读取 YAML 配置文件
def read_yaml(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error("读取 YAML 文件失败: %s", e)
        return None


def load_config(yaml_path):
    """从指定 YAML 文件读取目标目录位置和遍历深度"""
    config = read_yaml(yaml_path)
    if config is None:
        return ".", 1
    return config.get("target_directory", "."), config.get("depth", 1)


def find_mp4_files(directory, depth):
    """遍历目标目录下的 MP4 文件，支持遍历深度"""
    mp4_files = []
    for root, _, files in os.walk(directory):
        # 计算当前目录的深度
        relative_depth = root[len(directory) :].count(os.sep)
        if relative_depth >= depth:
            continue
        for file in files:
            if file.lower().endswith(".mp4"):
                mp4_files.append(os.path.join(root, file))
    return mp4_files


def rename_mp4_to_m4a(mp4_files):
    """将 MP4 文件重命名为 M4A"""
    for mp4_file in mp4_files:
        m4a_file = os.path.splitext(mp4_file)[0] + ".m4a"
        try:
            os.rename(mp4_file, m4a_file)
            logger.info("重命名: %s -> %s", mp4_file, m4a_file)
        except Exception as e:
            logger.error("重命名失败: %s -> %s, 错误: %s", mp4_file, m4a_file, e)


def rename_files_with_padding(directory, extension="m4a"):
    """遍历指定目录下的所有指定类型的文件（默认m4a），根据文件总数补零"""
    files = [f for f in os.listdir(directory) if f.lower().endswith(f".{extension}")]
    files.sort()
    total_files = len(files)
    if total_files == 0:
        logger.info("未找到 %s 文件", extension)
        return

    num_digits = len(str(total_files))
    for idx, file in enumerate(files, start=1):
        new_name = f"{str(idx).zfill(num_digits)}.{extension}"
        old_path = os.path.join(directory, file)
        new_path = os.path.join(directory, new_name)
        try:
            os.rename(old_path, new_path)
            logger.info("重命名: %s -> %s", old_path, new_path)
        except Exception as e:
            logger.error("重命名失败: %s -> %s, 错误: %s", old_path, new_path, e)


def find_subdirectories(directory, depth):
    """根据深度参数要求，返回指定目录下的子目录列表"""
    subdirectories = []
    for root, dirs, _ in os.walk(directory):
        relative_depth = root[len(directory) :].count(os.sep)
        if relative_depth < depth:
            subdirectories.extend(os.path.join(root, d) for d in dirs)
    return subdirectories


def convert_wma_to_m4a(directory):
    """将指定目录下的 WMA 文件转换为 M4A，音频参数转换为 AAC"""
    wma_files = [f for f in os.listdir(directory) if f.lower().endswith(".wma")]
    if not wma_files:
        logger.info("未找到 WMA 文件")
        return

    for wma_file in wma_files:
        wma_path = os.path.join(directory, wma_file)
        m4a_path = os.path.splitext(wma_path)[0] + ".m4a"
        try:
            # 使用 ffmpeg 进行格式转换，将 wmav2 转为 aac
            ffmpeg.input(wma_path).output(m4a_path, acodec="aac", ab="192k").run()
            logger.info("转换成功: %s -> %s", wma_path, m4a_path)
            # 删除原始 WMA 文件
            # os.remove(wma_path)
            # logger.info("删除原始 WMA 文件: %s", wma_path)
        except Exception as e:
            logger.error("转换失败: %s -> %s, 错误: %s", wma_path, m4a_path, e)


if __name__ == "__main__":

    yaml_path = "./audio_convert.yaml"  # 配置文件路径
    target_directory, depth = load_config(yaml_path)
    # logger.info("目标目录: %s, 遍历深度: %d", target_directory, depth)
    #
    # mp4_files = find_mp4_files(target_directory, depth)
    # logger.info(mp4_files)
    # if not mp4_files:
    #     logger.info("未找到 MP4 文件")
    #     return
    # logger.info("找到 %d 个 MP4 文件", len(mp4_files))
    # rename_mp4_to_m4a(mp4_files)

    # 查找指定深度的子目录
    subdirs = find_subdirectories(target_directory, depth)
    logger.info("找到的子目录: %s", subdirs)
    for dirs in subdirs:
        convert_wma_to_m4a(dirs)
