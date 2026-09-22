# -*- coding: utf-8 -*-
"""
smoke_test.py — 非交互跑 5 个 FTC 问题，验证 RAG 管道。

Usage (在仓库根):
    python scripts/smoke_test.py
"""
import os
import sys
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_classic.chains import RetrievalQA

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not DEEPSEEK_API_KEY or not ZHIPU_API_KEY:
    sys.exit("ERROR: DEEPSEEK_API_KEY or ZHIPU_API_KEY missing in .env")

DATA_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    "解释 v5.5 跷跷板累积机制",
    "双电机飞轮怎么布置?",
    "v5.5 极限多少分?",
    "game_analysis 里写了哪些关键规则?",
    "8 POLLEN 累积一次的物理依据是什么?",
]


def build_index():
    docs = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    ).load()
    print(f"[INDEX] 加载 {len(docs)} 个文档")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"[INDEX] 分成 {len(chunks)} 个 chunk")
    embeddings = ZhipuAIEmbeddings(model="embedding-2", api_key=ZHIPU_API_KEY)
    index = FAISS.from_documents(chunks, embeddings)
    index.save_local(str(INDEX_DIR))
    return index


def main():
    # 1. Build or load index
    if (INDEX_DIR / "index.faiss").exists():
        print("[INDEX] 发现已有索引, 直接加载...")
        embeddings = ZhipuAIEmbeddings(model="embedding-2", api_key=ZHIPU_API_KEY)
        index = FAISS.load_local(
            str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
        )
    else:
        print("[INDEX] 建新索引 (首次会慢一点)...")
        index = build_index()

    # 2. QA chain
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

    # 3. 跑 5 个问题
    for i, q in enumerate(QUESTIONS, 1):
        print()
        print("=" * 70)
        print(f"[Q{i}] {q}")
        print("=" * 70)
        try:
            r = qa.invoke({"query": q})
            print(f"\n[A]\n{r['result']}")
            print("\n[来源]")
            for j, d in enumerate(r["source_documents"], 1):
                src = d.metadata.get("source", "?")
                print(f"  [{j}] {src}")
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    print()
    print("=" * 70)
    print("smoke test 跑完")
    print("=" * 70)


if __name__ == "__main__":
    main()