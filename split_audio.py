"""批量音频切分工具

用途：
  将输入目录中的 MP3/M4A 按固定分钟数切分，并保留最后一个不足时长的片段。

配置文件：
  默认读取 config.yaml；时长、码率、输入和输出路径位于 flows.split_audio。

可选参数：
  --config-file  配置文件路径，默认 config.yaml。
  --input        临时覆盖输入目录。
  --output       临时覆盖输出目录。
  --max-files    限制本次处理文件数。

示例：
  python split_audio.py --max-files 1

输出：
  分段文件写入 output/split，并在控制台输出 JSON 汇总。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mp3_processor.bootstrap import bootstrap_context
from mp3_processor.cli import print_result
from mp3_processor.flows.split_audio_flow import run


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
