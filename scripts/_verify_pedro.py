# -*- coding: utf-8 -*-
"""验证 Pedro Pathing 文档进 RAG 后 Q3 能直接答"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 加载 .env
env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

if not os.environ.get("DEEPSEEK_API_KEY"):
    print("[ERROR] 没设 DEEPSEEK_API_KEY")
    sys.exit(1)

# 直接用 ultimate RAG 跑, 不走 ReAct agent, 看最纯净的 RAG 答案
from ultimate_rag import build_or_load_index, make_multi_query_chain, make_hyde_conservative_chain, make_reranker, make_ultimate_qa
from langchain_openai import ChatOpenAI

idx, _, _ = build_or_load_index()
llm = ChatOpenAI(
    model="deepseek-chat", temperature=0,
    base_url="https://api.deepseek.com/v1",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    timeout=120,
)
multi_chain = make_multi_query_chain(llm)
hyde_chain = make_hyde_conservative_chain(llm)
reranker = make_reranker()
qa = make_ultimate_qa(idx, multi_chain, hyde_chain, reranker, llm)

q = "FTC 机器人路径规划用什么算法? Pedro Pathing 跟 FTC 有什么关系?"
print(f"Q: {q}\n")

import time
t0 = time.time()
answer, sources = qa(q)
elapsed = time.time() - t0

print(f"[A] (took {elapsed:.1f}s)\n")
print(answer)
print(f"\n[Sources ({len(sources)})]")
for i, s in enumerate(sources):
    src = s.metadata.get("source", "?").split("\\")[-1]
    print(f"  [{i+1}] {src}")