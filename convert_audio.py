"""批量音频转换工具

用途：
  递归扫描输入目录，将 M4A、MP4 或 WMA 转换为 MP3，并在输出目录保留原目录层级。

配置文件：
  默认读取 config.yaml；common.env 可覆盖本机路径和日志级别。

可选参数：
  --config-file  配置文件路径，默认 config.yaml。
  --input        临时覆盖输入目录。
  --output       临时覆盖输出目录。
  --max-files    限制本次处理文件数，0 表示不限制。

示例：
  python convert_audio.py --max-files 1

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-file", default="config.yaml")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--max-files", type=int)
    args = parser.parse_args()
    context = bootstrap_context(__file__, args.config_file)
    return print_result(run(context, input_path=args.input, output_dir=args.output, max_files=args.max_files))


if __name__ == "__main__":
    raise SystemExit(main())
