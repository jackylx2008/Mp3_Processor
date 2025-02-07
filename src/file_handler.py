import glob
import logging
import os
import subprocess
import sys

from pydub import AudioSegment

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.logging_config import setup_logger  # 引入日志配置函数

# 初始化日志记录器
logger = setup_logger(log_level=logging.INFO, log_file="./logs/file_handler.log")


def is_valid_mp3(mp3_file):
    """
    使用 ffmpeg 检查 MP3 文件是否有效（能够成功解码）。
    :param mp3_file: MP3 文件路径
    :return: 如果文件有效，则返回 True，否则返回 False
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", mp3_file, "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            logger.error(
                "Invalid MP3 file: %s\nFFmpeg stderr: %s", mp3_file, result.stderr
            )
            return False
        return True
    except Exception as e:
        logger.error("Error checking MP3 file validity for %s: %s", mp3_file, e)
        return False


def export_segment_and_check(segment, output_file, max_retries=3):
    """
    将 segment 导出为 MP3 并检查文件是否有效。
    若无效则删除并重试，最多尝试 max_retries 次。

    :param segment: pydub 的 AudioSegment 对象
    :param output_file: 导出 MP3 文件的目标路径
    :param max_retries: 最大重试次数
    :return: True 表示导出成功且有效，False 表示最终仍然无效
    """
    for attempt in range(1, max_retries + 1):
        # 导出
        segment.export(output_file, format="mp3")

        # 检查有效性
        if is_valid_mp3(output_file):
            return True
        else:
            logger.warning(
                "Invalid file after split (attempt %d/%d): %s",
                attempt,
                max_retries,
                output_file,
            )
            # 无效则删除该文件
            try:
                os.remove(output_file)
            except OSError as e:
                logger.error("Failed to remove invalid file %s: %s", output_file, e)

            # 如果还有剩余重试次数，就继续重试
            if attempt < max_retries:
                logger.info("Retrying to export %s...", output_file)

    # 重试了多次都无效，返回 False
    return False


def split_mp3(
    input_file, split_duration=None, split_size=None, output_dir="./mp3_files/output"
):
    """
    根据给定的时长（分钟）或文件大小切割 MP3 文件，并显示进度。

    :param input_file: 输入的 MP3 文件路径。
    :param split_duration: 切割的时长（分钟），可选。
    :param split_size: 每个部分的文件大小（字节），可选。
    :param output_dir: 输出目录。
    :return: 切割后的文件路径列表。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 加载 MP3 文件
    try:
        audio = AudioSegment.from_mp3(input_file)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return []
    except IOError as e:
        logger.error("IO error while reading the MP3 file: %s", e)
        return []
    except Exception as e:
        logger.error("Error processing the MP3 file: %s", e)
        return []

    output_files = []
    logger.info("Starting to split: %s", input_file)

    if split_duration:
        # 按时长切割
        duration_ms = split_duration * 60 * 1000  # 转为毫秒
        num_parts = len(audio) // duration_ms
        for i in range(num_parts):
            start_time = i * duration_ms
            end_time = (i + 1) * duration_ms
            segment = audio[start_time:end_time]
            part_number = str(i + 1).zfill(len(str(num_parts)))  # 补零
            output_file = os.path.join(
                output_dir,
                f"{os.path.basename(input_file).replace('.mp3', '')}_part_{part_number}.mp3",
            )

            # 导出并检查
            success = export_segment_and_check(segment, output_file, max_retries=3)
            if success:
                output_files.append(output_file)
                progress = (i + 1) / num_parts * 100
                logger.info(
                    "Progress: Part %d/%d (%.2f%%) -> %s",
                    i + 1,
                    num_parts,
                    progress,
                    output_file,
                )
            else:
                logger.error(
                    "Failed to produce a valid MP3 segment for part %d/%d",
                    i + 1,
                    num_parts,
                )

    elif split_size:
        # 按文件大小切割
        file_size = os.path.getsize(input_file)
        num_parts = file_size // split_size
        segment_size = len(audio) // num_parts
        for i in range(num_parts):
            start_time = i * segment_size
            end_time = (i + 1) * segment_size
            segment = audio[start_time:end_time]
            part_number = str(i + 1).zfill(len(str(num_parts)))  # 补零
            output_file = os.path.join(
                output_dir,
                f"{os.path.basename(input_file).replace('.mp3', '')}_part_{part_number}.mp3",
            )

            # 导出并检查
            success = export_segment_and_check(segment, output_file, max_retries=3)
            if success:
                output_files.append(output_file)
                progress = (i + 1) / num_parts * 100
                logger.info(
                    "Progress: Part %d/%d (%.2f%%) -> %s",
                    i + 1,
                    num_parts,
                    progress,
                    output_file,
                )
            else:
                logger.error(
                    "Failed to produce a valid MP3 segment for part %d/%d",
                    i + 1,
                    num_parts,
                )

    else:
        logger.warning("Neither split_duration nor split_size was provided.")

    return output_files


def split_multiple_mp3(
    input_dir, split_duration=None, split_size=None, output_dir="./mp3_files/output"
):
    """
    批量处理输入目录下的所有 MP3 文件。

    :param input_dir: 输入的 MP3 文件目录。
    :param split_duration: 切割的时长（分钟），可选。
    :param split_size: 每个部分的文件大小（字节），可选。
    :param output_dir: 输出目录。
    :return: 处理完成后所有分割文件的列表
    """
    mp3_files = glob.glob(os.path.join(input_dir, "*.mp3"))
    if not mp3_files:
        logger.warning("No MP3 files found in directory: %s", input_dir)
        return []

    all_output_files = []
    for mp3_file in mp3_files:
        logger.info("Processing file: %s", mp3_file)
        output_files = split_mp3(mp3_file, split_duration, split_size, output_dir)
        all_output_files.extend(output_files)

    return all_output_files


if __name__ == "__main__":
    logger.info("Begin!")
    # 示例调用，切割 input 目录下的所有 MP3 文件，每个文件切割为 15 分钟
    split_multiple_mp3("./mp3_files/input", split_duration=15)
    logger.info("Done!")
# src/file_handler.p
