"""批量封面图片裁剪工具

用途：
  递归扫描图片目录，按 config.yaml 中的 crop_box 裁剪封面并保留目录层级。

配置文件：
  默认读取 config.yaml；输入、输出和裁剪区域位于 flows.prepare_cover。

可选参数：
  --config-file  配置文件路径，默认 config.yaml。
  --input        临时覆盖输入图片目录。
  --output       临时覆盖输出目录。
  --max-files    限制本次处理图片数。

示例：
  python prepare_cover.py --max-files 1

输出：
  裁剪图片写入 output/covers，并在控制台输出 JSON 汇总。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mp3_processor.bootstrap import bootstrap_context
from mp3_processor.cli import print_result
from mp3_processor.flows.prepare_cover_flow import run


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
