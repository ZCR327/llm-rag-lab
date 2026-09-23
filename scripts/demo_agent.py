# -*- coding: utf-8 -*-
"""LangGraph Web Agent demo - 跑 3 题验证 RAG + Web search 协作 (LangChain v1.0 API)"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 强制 UTF-8 输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# v0.1.17: import agent (触发 load_dotenv 自动加载 .env) 再检查 env var
import agent  # noqa
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

if not os.environ.get("DEEPSEEK_API_KEY"):
    print("[ERROR] 没设 DEEPSEEK_API_KEY (项目 .env 加载失败?)")
    sys.exit(1)

llm = ChatOpenAI(
    model="deepseek-chat", temperature=0,
    base_url="https://api.deepseek.com/v1",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    timeout=120,
)

tools = [agent.tool_rag_search, agent.tool_search_web, agent.tool_fetch_url]
react_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=agent.SYSTEM_PROMPT,
    debug=False,
)
print(f"[INFO] ReAct agent ready (LangChain v1.0)")
print(f"[INFO] tools: {[t.__name__ for t in tools]}")
print(f"[INFO] recursion_limit=20\n")

# 3 题: 1) 纯 RAG, 2) 纯 Web, 3) 混合
TESTS = [
    ("Q1 (RAG 优先)", "FTC 2026-2027 DECODE 游戏规则中翻倒 HIVE 有什么计分?"),
    ("Q2 (Web 优先)", "FIRST Tech Challenge DECODE 2026-2027 game manual 最新版本什么时候发布?"),
    ("Q3 (hybrid)", "FTC 机器人路径规划用什么算法? Pedro Pathing 跟 FTC 有什么关系?"),
]

import time
for tag, q in TESTS:
    print(f"\n{'='*70}")
    print(f"{tag}: {q}")
    print(f"{'='*70}")
    t0 = time.time()
    try:
        result = react_agent.invoke(
            {"messages": [("user", q)]},
            config={"recursion_limit": 20},
        )
        elapsed = time.time() - t0
        # 列出所有 tool 调用
        for msg in result["messages"]:
            if msg.type == "ai" and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    args_preview = str(tc["args"])[:100]
                    print(f"  -> {tc['name']}({args_preview})")
        # 最终答案
        for msg in reversed(result["messages"]):
            if msg.type == "ai" and not getattr(msg, "tool_calls", None):
                print(f"\n[A] (took {elapsed:.1f}s)\n{msg.content}")
                break
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
    print()