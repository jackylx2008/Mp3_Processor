"""批量音频元数据工具

用途：
  根据文件名生成标题，并批量设置 MP3/M4A 的艺术家和专辑标签。

配置文件：
  默认读取 config.yaml；艺术家、专辑和输入路径位于 flows.update_metadata。

可选参数：
  --config-file  配置文件路径，默认 config.yaml。
  --input        临时覆盖输入目录。
  --max-files    限制本次扫描文件数。
  --write        实际写入文件；未提供时仅预览，不修改业务数据。

示例：
  python update_metadata.py --max-files 5
  python update_metadata.py --write

输出：
  控制台输出 JSON 汇总；--write 会原地更新音频标签。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mp3_processor.bootstrap import bootstrap_context
from mp3_processor.cli import print_result
from mp3_processor.flows.update_metadata_flow import run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-file", default="config.yaml")
    parser.add_argument("--input")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    context = bootstrap_context(__file__, args.config_file)
    return print_result(run(context, input_path=args.input, write=args.write, max_files=args.max_files))


if __name__ == "__main__":
    raise SystemExit(main())
