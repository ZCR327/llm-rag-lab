# -*- coding: utf-8 -*-
"""横跨 9 主题的 RAG 覆盖测试"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

from ultimate_rag import (build_or_load_index, make_multi_query_chain,
                           make_hyde_conservative_chain, make_reranker, make_ultimate_qa)
from langchain_openai import ChatOpenAI
import time

idx, _, _ = build_or_load_index()
llm = ChatOpenAI(
    model="deepseek-chat", temperature=0,
    base_url="https://api.deepseek.com/v1",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    timeout=120,
)
multi = make_multi_query_chain(llm)
hyde = make_hyde_conservative_chain(llm)
rer = make_reranker()
qa = make_ultimate_qa(idx, multi, hyde, rer, llm)

# 9 主题 × 1-2 题 = 11 题
TESTS = [
    # 1. FTC 游戏分析
    ("FTC 游戏分析", "BIOBUZZ 2026-2027 的核心元素是什么? HIVE 怎么算分?"),
    # 2. FTC 设计演进
    ("FTC 设计演进", "24306 机器人从 v2 到 v5 砍了什么? 为什么砍?"),
    # 3. FTC brainstorm
    ("FTC brainstorm", "2026-09-13 那天 brainstorm 了哪些 idea?"),
    # 4. Pedro Pathing 算法
    ("Pedro 算法", "Pedro Pathing 用什么算法? Bézier 怎么算?"),
    # 5. Pedro Pathing Android 集成
    ("Pedro Android", "Android Studio 怎么集成 Pedro Pathing? 主要步骤?"),
    # 6. 飞机原理
    ("飞机原理", "737 MAX 两次失事的共同技术原因是什么?"),
    # 7. 智回社 CHANGELOG
    ("智回社 changelog", "v5.9 积分系统最近改了什么? CHANGELOG 说什么?"),
    # 8. 智回社 API
    ("智回社 API", "积分系统的 API 接口有哪些? 怎么调用登录?"),
    # 9. 智回社 HTTPS
    ("智回社 HTTPS", "HTTPS 怎么配置? 简要步骤"),
    # 10. 智回社 code review
    ("智回社 review", "v5.9 最近做过哪些 code review? 重要修复举例"),
    # 11. 智回社 daily analysis
    ("智回社 analysis", "2026-06-17 那天的 daily analysis 说啥了?"),
]

for topic, q in TESTS:
    print(f"\n{'='*70}")
    print(f"## {topic}")
    print(f"Q: {q}")
    print(f"{'='*70}")
    t0 = time.time()
    try:
        answer, sources = qa(q)
        elapsed = time.time() - t0
        # 显示完整答案（限 800 字符）
        ans = answer[:800]
        print(f"\n[A] (took {elapsed:.1f}s)\n{ans}")
        if len(answer) > 800:
            print(f"  ... (truncated, total {len(answer)} chars)")
        print(f"\n  [Sources ({len(sources)})]")
        for i, s in enumerate(sources):
            src = s.metadata.get("source", "?").split("\\")[-1]
            print(f"    [{i+1}] {src}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")