# ./src/cover_handler.py
import io
import logging
import os
import sys

import cv2
import eyed3
import numpy as np
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFont

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# 解决中文文件名问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from src.logging_config import setup_logger  # 引入日志配置函数

# 初始化日志记录器，日志文件为 cover_handler.log
logger = setup_logger(log_level=logging.INFO, log_file="./logs/cover_handler.log")


def images_cropper(
    input_dir, output_dir, crop_box, extensions=("jpg", "jpeg", "png", "bmp")
):
    """
    批量裁剪图片，PNG 文件保持原始清晰度和透明度。
    """
    logger.info(
        "开始批量裁剪图片，输入文件夹: %s, 输出文件夹: %s", input_dir, output_dir
    )

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.debug("创建输出文件夹: %s", output_dir)

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(extensions):
                input_path = os.path.join(root, file)
                output_path = os.path.join(output_dir, file)

                logger.info("正在处理文件: %s", input_path)

                try:
                    with Image.open(input_path) as img:
                        if img.format == "PNG":
                            img = img.convert("RGBA")
                        cropped_img = img.crop(crop_box)

                        if img.format == "PNG":
                            cropped_img.save(
                                output_path, format="PNG", compress_level=0
                            )
                        else:
                            cropped_img.save(output_path)

                        logger.info("已成功裁剪并保存文件: %s", output_path)
                except Exception as e:
                    logger.error("处理文件 %s 时出错: %s", input_path, e)

    logger.info("图片批量裁剪完成。")


def add_text_to_image(
    src_pic, des_pic, msg1, msg2, fontpath, font_color, font_size, font_offset, init_pos
):
    """
    在图片上添加指定文字，并保存为新图片。

    参数:
    --------
    src_pic : str
        源图片的路径，支持常见格式（如 .jpg, .png）。该图片作为背景。

    des_pic : str
        生成的带有文字的新图片的保存路径。

    msg1 : str
        要绘制在图片上的第一行文字（通常作为标题或章节名称）。如果为空，则不会绘制此行。

    msg2 : str
        要绘制在图片上的第二行文字（通常作为子标题或描述）。支持自动换行，确保文字不超出图片宽度。

    fontpath : str
        字体文件的路径（.ttf格式）。确保提供的路径正确，常用字体如微软雅黑（Yahei.ttf），或系统字体如 Arial。

    font_color : tuple
        文字颜色，格式为 (R, G, B, A)。例如，白色为 (255, 255, 255, 0)，黑色为 (0, 0, 0, 0)。

    font_size : int
        字体大小，单位为像素。根据图片大小调整合适的字体大小。

    font_offset : int
        每行文字的垂直偏移量，单位为像素。用于控制多行文字之间的间距。

    init_pos : float
        文字绘制在图片的垂直起始位置，相对于图片高度的比例。
        - 0.0 表示图片顶部，0.5 表示图片中间，1.0 表示图片底部。
        - 例如，`init_pos=0.8` 表示文字开始绘制在图片底部 80% 的位置。

    返回:
    --------
    img_with_text : np.ndarray
        加入文字后的图片，以 OpenCV 的格式返回（BGR通道），可用于进一步处理或显示。

    异常:
    --------
    FileNotFoundError:
        如果 `src_pic` 路径不存在或无法找到源图片。

    ValueError:
        如果无法读取图片（可能由于文件损坏或格式不支持）。

    示例:
    --------
    add_text_to_image(
        src_pic='./assets/cover_images/sample_cover.jpg',
        des_pic='./assets/cover_images/sample_cover_with_text.jpg',
        msg1='Chapter 1',
        msg2='The Boy Who Lived',
        fontpath='./assets/fonts/Yahei.ttf',
        font_color=(255, 255, 255, 0),
        font_size=50,
        font_offset=60,
        init_pos=0.8
    )
    """

    # 检查图片路径是否存在
    if not os.path.exists(src_pic):
        logger.error("图片路径 '%s' 不存在，请检查文件路径。", src_pic)
        raise FileNotFoundError(f"图片路径 '{src_pic}' 不存在。")

    # 读取图片
    img = cv2.imread(src_pic)

    if img is None:
        logger.error("无法读取图片 '%s'，请检查文件格式或文件是否损坏。", src_pic)
        raise ValueError(f"无法读取图片 '{src_pic}'，请检查文件格式或文件是否损坏。")

    # 转换为 PIL 格式进行文字绘制
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(fontpath, font_size)

    pic_W, pic_H = img_pil.size

    # 绘制第一行文字
    if msg1:
        _, _, w, h = draw.textbbox((0, 0), msg1, font=font)
        draw.text(
            (
                (pic_W - w) / 2,
                (pic_H - h) * init_pos,
            ),
            msg1,
            font=font,
            fill=font_color,
        )

    # 绘制第二行文字
    if msg2:
        # 绘制第二行中文，根据文字长度自动换行
        if draw.textlength(msg2, font) > pic_W:
            # 按照图片的宽对中文字符串进行切片分组
            str_pair = []
            begin = 0
            for end in range(len(msg2)):
                if draw.textlength(msg2[begin:end], font) > pic_W:
                    str_pair.append((begin, end - 1))
                    begin = end - 1
                    end = end - 1
            str_pair.append((begin, len(msg2)))

            # 按照字符串分组，居中绘制字符串
            i = 1
            for t in str_pair:
                _, _, w, h = draw.textbbox((0, 0), msg2[t[0] : t[1]], font=font)
                draw.text(
                    ((pic_W - w) / 2, (pic_H - h) * init_pos + font_offset * i),
                    msg2[t[0] : t[1]],
                    font=font,
                    fill=font_color,
                )
                i = i + 1

        else:
            _, _, w, h = draw.textbbox((0, 0), msg2, font=font)
            draw.text(
                ((pic_W - w) / 2, (pic_H - h) * init_pos + font_offset),
                msg2,
                font=font,
                fill=font_color,
            )
    # 转换回 OpenCV 格式
    img_with_text = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # 保存新图片
    cv2.imwrite(des_pic, img_with_text)
    logger.info("生成新的封面图片: %s，添加的文字: '%s %s'", des_pic, msg1, msg2)

    # 显示加过文字的图片（调试用）
    # cv2.imshow("Image with Text", img_with_text)
    # logger.info("显示已添加文字的图片。按任意键关闭窗口。")
    # cv2.waitKey(0)
    cv2.destroyAllWindows()

    return img_with_text


def remove_existing_cover(mp3_file_path):
    """
    删除 MP3 文件中已有的封面图片，确保不会因缺少标签而报错。
    """
    audiofile = eyed3.load(mp3_file_path)
    if audiofile.tag is None:
        audiofile.initTag()
        logger.warning("'%s' 没有 ID3 标签，已初始化。", mp3_file_path)

    if audiofile.tag.images:
        logger.info("'%s' 已有封面，正在删除旧封面。", mp3_file_path)
        audiofile.tag.images.remove("")
        audiofile.tag.save()
    else:
        logger.info("'%s' 没有检测到封面，无需删除。", mp3_file_path)


def add_cover_to_mp3(mp3_file_path, cover_image_path):
    """
    为 MP3 文件添加封面，使用 mutagen 确保兼容性。
    """
    try:
        audio = MP3(mp3_file_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        with open(cover_image_path, "rb") as img_file:
            audio.tags.add(
                APIC(
                    encoding=3,  # UTF-8 编码
                    mime="image/jpeg",
                    type=3,  # 封面类型：Front cover
                    desc="Cover",
                    data=img_file.read(),
                )
            )
        audio.save()
        logger.info("封面已成功添加到 '%s'。", mp3_file_path)
    except Exception as e:
        logger.error("无法为 '%s' 添加封面: %s", mp3_file_path, e)


def process_mp3_folder(
    mp3_folder, base_cover_image, split_char, fontpath="./Yahei.ttf"
):
    """
    批量处理文件夹中的 MP3 文件，根据文件名生成带文字的封面，并嵌入到 MP3 文件中。
    """
    for file in os.listdir(mp3_folder):
        if file.lower().endswith(".mp3"):
            mp3_file_path = os.path.join(mp3_folder, file)
            logger.info("正在处理文件: %s", mp3_file_path)

            # 提取文件名中的信息作为封面文字
            filename = os.path.splitext(file)[0]
            parts = filename.split(split_char)
            if len(parts) >= 2:
                title = parts[0].strip() + split_char
                description = parts[1].strip()
            else:
                title = filename
                description = ""

            # 在封面图片上添加文字
            output_cover_image = os.path.join(mp3_folder, "temp_cover.jpg")
            add_text_to_image(
                src_pic=base_cover_image,
                des_pic=output_cover_image,
                msg1=title,
                msg2=description,
                fontpath=fontpath,
                font_color=(255, 255, 255, 0),  # 白色字体
                font_size=120,
                font_offset=150,
                init_pos=0.1,
            )

            # 删除已有封面并添加新封面
            remove_existing_cover(mp3_file_path)
            add_cover_to_mp3(mp3_file_path, output_cover_image)

            # 删除临时封面文件
            os.remove(output_cover_image)
            logger.info("'%s' 处理完成！", file)


def batch_crop_images():
    """
    批量裁剪图片并保存到指定目录。
    """
    input_folder = "./assets/cover_images/input"  # 输入文件夹路径
    output_folder = "./assets/cover_images"  # 输出文件夹路径
    crop_area = (117, 745, 1177, 1805)  # 裁剪区域 (左, 上, 右, 下)

    images_cropper(input_folder, output_folder, crop_area)


if __name__ == "__main__":
    mp3_folder = "./mp3_files/output"  # MP3 文件夹路径
    base_cover_image = "./assets/cover_images/Harry_Pot_4.png"  # 封面图片路径

    if not os.path.exists(mp3_folder):
        logger.error("指定的文件夹 '%s' 不存在。", mp3_folder)
    elif not os.path.isfile(base_cover_image):
        logger.error("指定的封面图片 '%s' 不存在。", base_cover_image)
    else:
        logger.info("开始为 '%s' 中的 MP3 文件添加封面。", mp3_folder)
        process_mp3_folder(mp3_folder, base_cover_image, split_char="》")
        logger.info("所有 MP3 文件封面处理完成。")
