# -*- coding: utf-8 -*-
"""
smoke_test_extended.py — 扩展题库 (6 文档: 5 FTC + 1 飞机基本原理)

设计意图:
- 5 个 FTC 题目: 旧库应能答 (FTC 文档里有)
- 3 个飞机题目: 旧库应能答 (飞机文档里有)
- 3 个 FTC + 飞机混合题: 测试 RAG 在多主题混合下的检索精度
- 3 个完全 out-of-distribution 题: 验证 "老实说不知道" 行为
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
import advanced_rag  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

QUESTIONS = [
    # === FTC 题目 (5 个, 旧库可答) ===
    "解释 v5.5 跷跷板累积机制",
    "双电机飞轮怎么布置?",
    "v5.5 极限多少分?",
    "game_analysis 里写了哪些关键规则?",
    "8 POLLEN 累积一次的物理依据是什么?",
    # === 飞机原理题目 (3 个, 新库可答) ===
    "手搓飞机的升力是怎么产生的?",
    "迎角 (Angle of Attack) 是什么? 多少度最佳?",
    "纸飞机投掷时为什么要用微旋转?",
    # === 混合题 (3 个, 测试检索精度) ===
    "v5.5 翻倒和飞机失速有什么相似原理?",
    "机器人装载槽倾斜 -5 度 跟飞机迎角设计有什么区别?",
    "FTC 远射跟纸飞机投掷的物理基础有何不同?",
    # === OOD 题目 (3 个, 应老实说不知道) ===
    "黑洞是怎么形成的?",
    "费马大定理的证明思路是什么?",
    "二次方程求根公式怎么来的?",
]


def main():
    print("=" * 70)
    print("  Extended smoke test (6 文档, 14 问题)")
    print("=" * 70)

    print("\n[INIT] 重建索引 (含 飞机基本原理.md)...")
    index, n_docs, n_chunks = advanced_rag.build_or_load_index()
    print(f"[INIT] 文档数: {n_docs}, chunk 数: {n_chunks}")

    rewriter = advanced_rag.make_query_rewriter()
    reranker = advanced_rag.make_reranker()
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
        print("#" * 70)
        print(f"# [Q{i:2d}] {q}")
        print("#" * 70)
        t0 = time.time()
        try:
            answer, sources = qa(q)
            elapsed = time.time() - t0
            print(f"\n[A] (took {elapsed:.1f}s)\n{answer}")
            print(f"\n[Sources: {len(sources)} docs after rerank]")
            for j, doc in enumerate(sources, 1):
                src = doc.metadata.get("source", "?")
                # Extract filename from path
                if "\\" in src:
                    fname = src.split("\\")[-1]
                else:
                    fname = src
                print(f"  [{j}] {fname}")
        except Exception as e:
            print(f"[ERROR] {e}")

    print()
    print("=" * 70)
    print("extended smoke test 跑完")
    print("=" * 70)


if __name__ == "__main__":
    main()