import logging
import os
import random
import sys
import time

import pygame

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.logging_config import setup_logger  # 引入日志配置函数

# 初始化日志记录器，日志文件为 test_mp3_output.log
logger = setup_logger(log_level=logging.INFO, log_file="./logs/test_mp3_output.log")


def initialize_pygame():
    """初始化 Pygame 及其音频系统"""
    pygame.init()
    pygame.mixer.init()
    # 创建一个小窗口来捕获键盘事件
    pygame.display.set_mode((100, 100))
    pygame.display.set_caption("MP3 Player")


def play_mp3_files_in_folder(folder_path, play_duration_seconds):
    """播放指定文件夹中的MP3文件"""
    # 获取文件夹中所有MP3文件
    mp3_files = [f for f in os.listdir(folder_path) if f.endswith(".mp3")]
    mp3_files.sort()
    logger.info("发现 %d 个MP3文件，开始播放...", len(mp3_files))

    program_running = True  # 控制整个程序是否运行
    for mp3_file in mp3_files:
        if not program_running:
            break

        mp3_path = os.path.join(folder_path, mp3_file)
        logger.info("正在播放: %s", mp3_file)

        try:
            # 加载并获取音频信息
            sound = pygame.mixer.Sound(mp3_path)
            total_length = sound.get_length()
            start_pos = random.uniform(0, max(0, total_length - play_duration_seconds))

            # 加载并播放MP3
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play(start=start_pos)

            logger.info(
                "播放 %s，从 %d 秒开始，时长 %d 秒...",
                mp3_file,
                start_pos,
                play_duration_seconds,
            )

            start_time = time.time()
            clock = pygame.time.Clock()
            current_file_playing = True  # 控制当前文件是否继续播放

            while (
                time.time() - start_time < play_duration_seconds
                and current_file_playing
            ):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        program_running = False
                        current_file_playing = False
                        pygame.mixer.music.stop()
                        break
                    elif event.type == pygame.KEYDOWN:
                        logger.info("检测到按键，跳过当前文件")
                        current_file_playing = False  # 只结束当前文件的播放
                        pygame.mixer.music.stop()
                        break

                clock.tick(30)  # 降低CPU使用率

            time.sleep(0.1)  # 短暂暂停，确保音频完全停止

        except Exception as e:
            logger.error("播放文件 %s 时发生错误: %s", mp3_file, str(e))
            continue

    if program_running:  # 只有在正常播放完所有文件时才显示此消息
        logger.info("所有文件播放完成")
    else:
        logger.info("程序被手动终止")

    pygame.quit()


if __name__ == "__main__":
    try:
        initialize_pygame()
        folder_path = "./mp3_files/output"  # 替换成你的文件夹路径
        play_duration_seconds = 5  # 每首歌播放5秒
        play_mp3_files_in_folder(folder_path, play_duration_seconds)
    except KeyboardInterrupt:
        logger.info("程序被手动中断")
        pygame.quit()
    except Exception as e:
        logger.error("程序运行出错: %s", str(e))
        pygame.quit()
