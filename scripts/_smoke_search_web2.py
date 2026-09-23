# -*- coding: utf-8 -*-
"""smoke test 2 - 纯英文 + 中文混合 query"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import agent

tests = [
    "FIRST Tech Challenge DECODE 2026-2027 game",
    "LangGraph create_react_agent documentation",
    "宏文学校 FTC 队伍",
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