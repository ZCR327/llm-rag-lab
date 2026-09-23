# -*- coding: utf-8 -*-
"""验证智回社文档进 RAG 后能答"""
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

q = "智能回收社 积分系统 v5.9 的技术架构是什么?"
import time
t0 = time.time()
answer, sources = qa(q)
elapsed = time.time() - t0
print(f"[A] (took {elapsed:.1f}s)\n{answer}\n")
print(f"[Sources ({len(sources)})]")
for i, s in enumerate(sources):
    src = s.metadata.get("source", "?").split("\\")[-1]
    print(f"  [{i+1}] {src}")