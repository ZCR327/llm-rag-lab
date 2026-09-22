# -*- coding: utf-8 -*-
"""
smoke_test_v014.py — 14 题 × v0.1.14 终极版 (multi-query + hyde 保守)
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

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ultimate_rag  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

QUESTIONS = [
    "解释 v5.5 跷跷板累积机制",
    "双电机飞轮怎么布置?",
    "v5.5 极限多少分?",
    "game_analysis 里写了哪些关键规则?",
    "8 POLLEN 累积一次的物理依据是什么?",
    "手搓飞机的升力是怎么产生的?",
    "迎角 (Angle of Attack) 是什么? 多少度最佳?",
    "纸飞机投掷时为什么要用微旋转?",
    "v5.5 翻倒和飞机失速有什么相似原理?",
    "机器人装载槽倾斜 -5 度 跟飞机迎角设计有什么区别?",
    "FTC 远射跟纸飞机投掷的物理基础有何不同?",
    "黑洞是怎么形成的?",
    "费马大定理的证明思路是什么?",
    "二次方程求根公式怎么来的?",
]


def main():
    print("=" * 70)
    print("  v0.1.14 Ultimate RAG (multi-query + hyde 保守 + rerank)")
    print("=" * 70)

    print("\n[INIT] 加载 v0.1.14...")
    index, _, _ = ultimate_rag.build_or_load_index()
    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        timeout=120,
    )
    multi_chain = ultimate_rag.make_multi_query_chain(llm)
    hyde_chain = ultimate_rag.make_hyde_conservative_chain(llm)
    reranker = ultimate_rag.make_reranker()
    qa = ultimate_rag.make_ultimate_qa(index, multi_chain, hyde_chain, reranker, llm)

    for i, q in enumerate(QUESTIONS, 1):
        print()
        print("=" * 70)
        print(f"# [Q{i:2d}] {q}")
        print("=" * 70)
        t0 = time.time()
        try:
            answer, sources = qa(q)
            elapsed = time.time() - t0
            print(f"\n[A] (took {elapsed:.1f}s)\n{answer}")
            for j, doc in enumerate(sources, 1):
                src = doc.metadata.get("source", "?").split("\\")[-1]
                print(f"  [{j}] {src}")
        except Exception as e:
            print(f"[ERROR] {e}")

    print()
    print("=" * 70)
    print("v0.1.14 跑完")
    print("=" * 70)


if __name__ == "__main__":
    main()