# -*- coding: utf-8 -*-
"""简化版 benchmark — 只输出每题判定结果 (空/部分/完整) + 时间"""
import sys, os, re
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
qa = make_ultimate_qa(
    idx,
    make_multi_query_chain(llm),
    make_hyde_conservative_chain(llm),
    make_reranker(),
    llm,
)

TESTS = [
    ("Q1 BIOBUZZ 元素", "BIOBUZZ 2026-2027 核心元素是什么? HIVE 计分?"),
    ("Q2 v2→v5 设计演进", "24306 机器人从 v2 到 v5 砍了什么? 为什么?"),
    ("Q3 9.13 brainstorm", "2026-09-13 brainstorm 了哪些 idea?"),
    ("Q4 Pedro 算法 Bézier", "Pedro Pathing 用什么算法? Bézier 怎么算?"),
    ("Q5 Pedro Android 集成", "Android Studio 集成 Pedro Pathing 主要步骤?"),
    ("Q6 737 MAX 失事", "737 MAX 两次失事共同技术原因?"),
    ("Q7 v5.9 CHANGELOG", "v5.9 积分系统最近改了什么?"),
    ("Q8 API 接口", "积分系统 API 接口有哪些? 怎么调用?"),
    ("Q9 HTTPS 配置", "HTTPS 配置简要步骤?"),
    ("Q10 code review 修复", "v5.9 重要 code review 修复举例?"),
    ("Q11 6.17 daily analysis", "2026-06-17 daily analysis 说啥?"),
]

print(f"{'#':<3} {'题目':<25} {'时间':<7} {'状态':<5} {'chars':<6}")
print("-" * 55)

results = []
for i, (name, q) in enumerate(TESTS, 1):
    t0 = time.time()
    try:
        answer, sources = qa(q)
        elapsed = time.time() - t0
        n = len(answer)
        # 判定: "资料未提供" + <100 chars = 空; 100-500 = 部分; >500 = 完整
        no_data = "资料未提供" in answer[:200] and n < 200
        if no_data:
            status = "❌空"
        elif n < 300:
            status = "⚠部分"
        else:
            status = "✅答"
        results.append((name, elapsed, status, n))
        print(f"{i:<3} {name:<25} {elapsed:.1f}s  {status}  {n}")
    except Exception as e:
        results.append((name, 0, f"❌{type(e).__name__}", 0))
        print(f"{i:<3} {name:<25} ERROR  {type(e).__name__}")

print("-" * 55)
empty = sum(1 for _, _, s, _ in results if s.startswith("❌"))
partial = sum(1 for _, _, s, _ in results if s.startswith("⚠"))
full = sum(1 for _, _, s, _ in results if s.startswith("✅"))
total_t = sum(t for _, t, _, _ in results)
print(f"\n汇总: ✅ {full}/11 + ⚠ {partial}/11 + ❌ {empty}/11")
print(f"     总耗时 {total_t:.1f}s, 平均 {total_t/11:.1f}s/题")