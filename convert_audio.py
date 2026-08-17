"""批量音频转换工具

用途：
  递归扫描输入目录，将指定源格式转换为目标格式，并在输出目录保留原目录层级。

配置文件：
  默认读取 config.yaml；common.env 可覆盖本机路径和日志级别。

可选参数：
  --config-file  配置文件路径，默认 config.yaml。
  --input        临时覆盖输入目录。
  --output       临时覆盖输出目录。
  --input-type   输入格式，可指定多个，例如 --input-type mp3 m4a wav。
  --output-type  输出格式：mp3、m4a、wma、wav、flac 或 ogg。
  --workers      并发转换数，默认读取配置（推荐 8）。
  --max-files    限制本次处理文件数，0 表示不限制。

示例：
  python convert_audio.py --input-type mp3 m4a --output-type flac --max-files 1

输出：
  转换文件写入 config.yaml 指定的 output/converted，并在控制台输出 JSON 汇总。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mp3_processor.bootstrap import bootstrap_context
from mp3_processor.cli import print_result
from mp3_processor.flows.convert_audio_flow import run


INPUT_TYPES = ("mp3", "m4a", "mp4", "wma", "wav", "flac", "ogg")
OUTPUT_TYPES = ("mp3", "m4a", "wma", "wav", "flac", "ogg")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-file", default="config.yaml")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--input-type", "--input-types", nargs="+", choices=INPUT_TYPES)
    parser.add_argument("--output-type", choices=OUTPUT_TYPES)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--max-files", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    context = bootstrap_context(__file__, args.config_file)
    return print_result(
        run(
            context,
            input_path=args.input,
            output_dir=args.output,
            input_extensions=args.input_type,
            output_type=args.output_type,
            workers=args.workers,
            max_files=args.max_files,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
