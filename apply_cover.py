"""批量写入音频封面工具

用途：
  将同一张 PNG/JPEG 封面递归写入 MP3、M4A 或 WMA 文件。

配置文件：
  默认读取 config.yaml；输入目录和封面路径位于 flows.apply_cover。

可选参数：
  --config-file  配置文件路径，默认 config.yaml。
  --input        临时覆盖输入目录。
  --cover        临时覆盖封面图片路径。
  --max-files    限制本次扫描文件数。
  --write        实际写入文件；未提供时仅预览。

示例：
  python apply_cover.py --cover assets/cover_images/sample.png --max-files 5
  python apply_cover.py --cover assets/cover_images/sample.png --write

输出：
  控制台输出 JSON 汇总；--write 会原地更新音频封面。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mp3_processor.bootstrap import bootstrap_context
from mp3_processor.cli import print_result
from mp3_processor.flows.apply_cover_flow import run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-file", default="config.yaml")
    parser.add_argument("--input")
    parser.add_argument("--cover")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    context = bootstrap_context(__file__, args.config_file)
    return print_result(
        run(context, input_path=args.input, cover_image=args.cover, write=args.write, max_files=args.max_files)
    )


if __name__ == "__main__":
    raise SystemExit(main())
