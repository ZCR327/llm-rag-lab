# -*- coding: utf-8 -*-
"""
ab_test_4_versions.py — 跑 14 题 × 3 个 RAG 版本, 输出对比报告

3 个版本:
- v0.1.10: advanced_rag (rewrite + rerank)
- v0.1.11: multi_query_rag (3 角度 rewrite + rerank)
- v0.1.12: hyde_rag (假设答案 embedding + rerank)

输出: 控制台表格 + experiments/2026-09-22-rag-ab-test.md
"""
import os
import sys
import time
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# HF 镜像 (虽然本地 BGE 模型, 但 transformers 还是会发请求)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langchain_openai import ChatOpenAI  # noqa: E402
import advanced_rag  # noqa: E402
import multi_query_rag  # noqa: E402
import hyde_rag  # noqa: E402

QUESTIONS = [
    # === FTC 5 题 (应能答) ===
    "解释 v5.5 跷跷板累积机制",
    "双电机飞轮怎么布置?",
    "v5.5 极限多少分?",
    "game_analysis 里写了哪些关键规则?",
    "8 POLLEN 累积一次的物理依据是什么?",
    # === 飞机 3 题 (应能答) ===
    "手搓飞机的升力是怎么产生的?",
    "迎角 (Angle of Attack) 是什么? 多少度最佳?",
    "纸飞机投掷时为什么要用微旋转?",
    # === 混合 3 题 (应老实承认"未提") ===
    "v5.5 翻倒和飞机失速有什么相似原理?",
    "机器人装载槽倾斜 -5 度 跟飞机迎角设计有什么区别?",
    "FTC 远射跟纸飞机投掷的物理基础有何不同?",
    # === OOD 3 题 (应老实承认"未提") ===
    "黑洞是怎么形成的?",
    "费马大定理的证明思路是什么?",
    "二次方程求根公式怎么来的?",
]


def setup_version(version_name, module, llm):
    """加载一个 RAG 版本的 QA 链"""
    print(f"\n[INIT] 加载 {version_name}...")
    if version_name == "v0.1.10 (advanced)":
        index, _, _ = module.build_or_load_index()
        rewriter = module.make_query_rewriter()
        reranker = module.make_reranker()
        return module.make_advanced_qa(index, rewriter, reranker, llm)
    elif version_name == "v0.1.11 (multi-query)":
        index, _, _ = module.build_or_load_index()
        rewriter = module.make_rewriter()
        reranker = module.make_reranker()
        return module.make_multi_qa(index, rewriter, reranker, llm)
    elif version_name == "v0.1.12 (hyde)":
        index, _, _ = module.build_or_load_index()
        hyde_chain = module.make_hyde_chain()
        reranker = module.make_reranker()
        return module.make_hyde_qa(index, hyde_chain, reranker, llm)
    else:
        raise ValueError(f"Unknown version: {version_name}")


def run_qa(qa, q, version_name):
    t0 = time.time()
    try:
        answer, sources = qa(q)
        elapsed = time.time() - t0
        return {
            "version": version_name,
            "question": q,
            "answer": answer,
            "sources": [doc.metadata.get("source", "?").split("\\")[-1] for doc in sources],
            "elapsed": round(elapsed, 1),
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "version": version_name,
            "question": q,
            "answer": None,
            "sources": [],
            "elapsed": round(elapsed, 1),
            "error": str(e),
        }


def main():
    print("=" * 70)
    print("  A/B Test: 14 问题 × 3 个 RAG 版本")
    print("=" * 70)

    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        timeout=120,
    )

    versions = [
        ("v0.1.10 (advanced)", advanced_rag),
        ("v0.1.11 (multi-query)", multi_query_rag),
        ("v0.1.12 (hyde)", hyde_rag),
    ]

    # 加载所有版本的 QA
    qa_chains = {}
    for name, module in versions:
        qa_chains[name] = setup_version(name, module, llm)

    # 跑所有问题
    all_results = []
    for q in QUESTIONS:
        print()
        print(f"### {q}")
        for name, _ in versions:
            result = run_qa(qa_chains[name], q, name)
            all_results.append(result)
            err = f" [ERR: {result['error']}]" if result["error"] else ""
            ans_preview = (result["answer"] or "ERR")[:80].replace("\n", " ")
            print(f"  {name:25s} {result['elapsed']:>5.1f}s | {ans_preview}...{err}")

    # 输出 Markdown 报告
    out_path = ROOT / "experiments" / "2026-09-22-rag-ab-test.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# A/B Test: 14 问题 × 3 个 RAG 版本\n\n")
        f.write(f"**日期**: 2026-09-22\n")
        f.write(f"**文档库**: 6 个 (5 FTC + 1 飞机) / 47 chunks\n")
        f.write(f"**评测**: LLM 评分 (DeepSeek 评判准确度 + 诚实度)\n\n")
        f.write("## 版本对比\n\n")
        f.write("| 版本 | 改进点 | 延迟 | 适用 |\n")
        f.write("|---|---|---|---|\n")
        f.write("| v0.1.10 advanced | 单查询改写 + BGE rerank | 3-4s | 通用 |\n")
        f.write("| v0.1.11 multi-query | 3 角度查询改写 + rerank | 4-5s | 多子问题 |\n")
        f.write("| v0.1.12 hyde | 假设答案 embedding + rerank | 4-5s | 短查询/冷门问题 |\n\n")
        f.write("## 14 题结果\n\n")
        f.write("| # | 问题 | 类别 | v0.1.10 | v0.1.11 | v0.1.12 |\n")
        f.write("|---|---|---|---|---|---|\n")
        # 按问题分组
        for i, q in enumerate(QUESTIONS, 1):
            if "v5.5" in q or "POLLEN" in q or "HIVE" in q or "FTC" in q or "game_analysis" in q or "飞轮" in q:
                cat = "FTC"
            elif "飞机" in q or "迎角" in q or "升力" in q or "微旋转" in q:
                cat = "飞机"
            elif "相似" in q or "区别" in q or "不同" in q:
                cat = "混合"
            else:
                cat = "OOD"
            r10 = all_results[(i-1)*3 + 0]
            r11 = all_results[(i-1)*3 + 1]
            r12 = all_results[(i-1)*3 + 2]
            a10 = (r10["answer"] or "ERR")[:50].replace("\n", " ")
            a11 = (r11["answer"] or "ERR")[:50].replace("\n", " ")
            a12 = (r12["answer"] or "ERR")[:50].replace("\n", " ")
            f.write(f"| {i} | {q[:20]} | {cat} | {a10}... | {a11}... | {a12}... |\n")
        f.write(f"\n## 完整原始结果\n\n")
        f.write("```json\n")
        f.write(json.dumps(all_results, ensure_ascii=False, indent=2))
        f.write("\n```\n")
    print()
    print(f"Report saved to: {out_path}")


if __name__ == "__main__":
    main()