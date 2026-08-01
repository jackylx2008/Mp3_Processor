"""入口脚本共用的结果输出。"""

from __future__ import annotations

import json

from mp3_processor.results import FlowResult


def print_result(result: FlowResult) -> int:
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1
