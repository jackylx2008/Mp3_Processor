import glob
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            ["ffmpeg", "-v", "quiet", "-i", mp3_file, "-t", "5", "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Invalid MP3 file: %s", mp3_file)
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
        segment.export(output_file, format="mp3")
        if is_valid_mp3(output_file):
            return True
        else:
            logger.warning(
                "Invalid file after split (attempt %d/%d): %s",
                attempt,
                max_retries,
                output_file,
            )
            try:
                os.remove(output_file)
            except OSError as e:
                logger.error("Failed to remove invalid file %s: %s", output_file, e)
            if attempt < max_retries:
                logger.info("Retrying to export %s...", output_file)
    return False


def split_mp3(
    input_file, split_duration=None, split_size=None, output_dir="./mp3_files/output"
):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    try:
        audio = AudioSegment.from_mp3(input_file)
    except Exception as e:
        logger.error("Error processing the MP3 file %s: %s", input_file, e)
        return []

    output_files = []
    logger.info("Starting to split: %s", input_file)

    if split_duration:
        duration_ms = split_duration * 60 * 1000
        num_parts = len(audio) // duration_ms
        for i in range(num_parts):
            start_time = i * duration_ms
            end_time = (i + 1) * duration_ms
            segment = audio[start_time:end_time]
            part_number = str(i + 1).zfill(len(str(num_parts)))
            output_file = os.path.join(
                output_dir,
                f"{os.path.basename(input_file).replace('.mp3', '')}_part_{part_number}.mp3",
            )
            if export_segment_and_check(segment, output_file, max_retries=3):
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
    return output_files


def precheck_mp3_file(mp3_file):
    if not is_valid_mp3(mp3_file):
        logger.error("Skipping invalid MP3 file: %s", mp3_file)
        return False
    return True


def split_multiple_mp3_parallel(
    input_dir,
    split_duration=None,
    split_size=None,
    output_dir="./mp3_files/output",
    max_workers=8,
):
    mp3_files = glob.glob(os.path.join(input_dir, "*.mp3"))
    if not mp3_files:
        logger.warning("No MP3 files found in directory: %s", input_dir)
        return []

    all_output_files = []

    def process_file(mp3_file):
        if not precheck_mp3_file(mp3_file):
            return []
        logger.info("Processing file: %s", mp3_file)
        return split_mp3(mp3_file, split_duration, split_size, output_dir)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_file, mp3_file): mp3_file for mp3_file in mp3_files
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_output_files.extend(result)

    return all_output_files


if __name__ == "__main__":
    logger.info("Begin batch processing!")
    split_multiple_mp3_parallel("./mp3_files/input", split_duration=15)
    logger.info("Batch processing completed!")
