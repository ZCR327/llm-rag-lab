# -*- coding: utf-8 -*-
"""
smoke_test_v2.py — 跑 5 个 FTC 问题, 验证 Advanced RAG 管道 (rewrite + rerank).

Usage: python scripts/smoke_test_v2.py
"""
import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 国内访问 HuggingFace 不稳, 在 import 任何 HF 库前先设镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Add src to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import advanced_rag  # noqa: E402

QUESTIONS = [
    "解释 v5.5 跷跷板累积机制",
    "双电机飞轮怎么布置?",
    "v5.5 极限多少分?",
    "game_analysis 里写了哪些关键规则?",
    "8 POLLEN 累积一次的物理依据是什么?",
]


def main():
    print("[INIT] 加载 index...")
    index = advanced_rag.build_or_load_index()
    print("[INIT] 加载 query rewriter (DeepSeek)...")
    rewriter = advanced_rag.make_query_rewriter()
    print("[INIT] 加载 reranker (BGE-reranker-base)...")
    reranker = advanced_rag.make_reranker()

    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        timeout=120,
    )
    qa = advanced_rag.make_advanced_qa(index, rewriter, reranker, llm)

    for i, q in enumerate(QUESTIONS, 1):
        print()
        print("=" * 70)
        print(f"[Q{i}] {q}")
        print("=" * 70)
        t0 = time.time()
        try:
            answer, sources = qa(q)
            elapsed = time.time() - t0
            print(f"\n[A] (took {elapsed:.1f}s)\n{answer}")
            print("\n[Top sources after rerank]")
            for j, doc in enumerate(sources, 1):
                src = doc.metadata.get("source", "?")
                print(f"  [{j}] {src}")
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    print()
    print("=" * 70)
    print("smoke test v2 跑完 (Advanced RAG: rewrite + rerank)")
    print("=" * 70)


if __name__ == "__main__":
    main()