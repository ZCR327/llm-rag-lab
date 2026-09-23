# -*- coding: utf-8 -*-
"""smoke test cn.bing.com search backend"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import agent

# Test 3 个不同 query, 各取前 3 结果
tests = [
    "FIRST Robotics 2026 game rules",
    "FTC 24306 团队",
    "DeepSeek V3 model card",
]

for q in tests:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print(f"{'='*60}")
    try:
        out = agent.tool_search_web(q, 3)
        print(out)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")