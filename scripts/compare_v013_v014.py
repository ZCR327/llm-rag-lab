# -*- coding: utf-8 -*-
"""
compare_v013_v014.py — 并排输出 v0.1.3 basic RAG vs v0.1.4 advanced RAG (rewrite + rerank)

5 个问题, 直接对比两个版本答案.

Usage: python scripts/compare_v013_v014.py
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

# HF 镜像（避免国内连不上 huggingface.co）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

# 提前 import minimal_rag + advanced_rag 触发 setdefault
import minimal_rag  # noqa: E402
import advanced_rag  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from langchain_classic.chains import RetrievalQA  # noqa: E402

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
ZHIPU_API_KEY = os.environ["ZHIPU_API_KEY"]

QUESTIONS = [
    "解释 v5.5 跷跷板累积机制",
    "双电机飞轮怎么布置?",
    "v5.5 极限多少分?",
    "game_analysis 里写了哪些关键规则?",
    "8 POLLEN 累积一次的物理依据是什么?",
]


def setup_basic():
    """v0.1.3: basic RAG, top-3 retrieval, no rewrite, no rerank"""
    index, n_docs, n_chunks = minimal_rag.build_or_load_index()
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        timeout=120,
    )
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=index.as_retriever(search_kwargs={"k": 3}),
        return_source_documents=True,
    )
    return qa


def setup_advanced():
    """v0.1.4: Advanced RAG, rewrite + top-10 + rerank + top-3"""
    index, n_docs, n_chunks = advanced_rag.build_or_load_index()
    rewriter = advanced_rag.make_query_rewriter()
    reranker = advanced_rag.make_reranker()
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        timeout=120,
    )
    qa = advanced_rag.make_advanced_qa(index, rewriter, reranker, llm)
    return qa


def main():
    print("=" * 80)
    print("  对比: v0.1.3 (basic) vs v0.1.4 (rewrite + rerank)")
    print("=" * 80)

    print("\n[INIT] 加载 v0.1.3 basic RAG...")
    basic_qa = setup_basic()
    print("[INIT] 加载 v0.1.4 advanced RAG (含 BGE reranker)...")
    adv_qa = setup_advanced()

    for i, q in enumerate(QUESTIONS, 1):
        print()
        print("#" * 80)
        print(f"# [Q{i}] {q}")
        print("#" * 80)

        # v0.1.3 basic
        print()
        print(">>> v0.1.3 (basic RAG, top-3 retrieval, no rewrite/rerank)")
        t0 = time.time()
        try:
            r = basic_qa.invoke({"query": q})
            elapsed = time.time() - t0
            print(f"({elapsed:.1f}s)")
            print(r["result"])
            print(f"\n[Sources: {len(r['source_documents'])} docs]")
        except Exception as e:
            print(f"[ERROR] {e}")

        # v0.1.4 advanced
        print()
        print(">>> v0.1.4 (Advanced: DeepSeek rewrite → top-10 → BGE rerank → top-3)")
        t0 = time.time()
        try:
            answer, sources = adv_qa(q)
            elapsed = time.time() - t0
            print(f"({elapsed:.1f}s)")
            print(answer)
            print(f"\n[Sources: {len(sources)} docs after rerank]")
        except Exception as e:
            print(f"[ERROR] {e}")

    print()
    print("=" * 80)
    print("对比完成")
    print("=" * 80)


if __name__ == "__main__":
    main()