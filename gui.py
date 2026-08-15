"""Mp3 Processor 统一桌面界面入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mp3_processor.gui.app import run_gui


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-file", default="ui_config.yaml", help="UI 配置文件路径")
    args = parser.parse_args()
    config_path = Path(args.config_file).expanduser()
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    try:
        return run_gui(PROJECT_ROOT, config_path)
    except Exception as exc:
        print(f"GUI 启动失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
