# -*- coding: utf-8 -*-
"""
minimal_rag.py — minimal end-to-end RAG demo (Lewis et al. 2020 style)

Pipeline: load docs -> chunk -> embed (ZhipuAI GLM Embedding-2) ->
FAISS index -> retrieve top-k -> generate (DeepSeek Chat) -> answer with sources.

Provider choice (2026-09-20):
- Embedding: ZhipuAI embedding-2 (国内直连, 免费)
- Chat: DeepSeek deepseek-chat (国内直连, 跟 OpenAI API 99% 兼容)

Setup:
    1. cp .env.example .env  (set DEEPSEEK_API_KEY + ZHIPU_API_KEY)
    2. Put some .txt files in data/raw/
    3. python src/minimal_rag.py

Windows UTF-8: this script auto-sets stdout to utf-8 so Chinese answers print cleanly.
"""
import logging
import os
import sys
from pathlib import Path

# --- Windows UTF-8 fix: avoid GBK encoding errors on Chinese output ---
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

# --- logging (more useful than print for debugging) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rag")

# --- config ---
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

if not DEEPSEEK_API_KEY or not ZHIPU_API_KEY:
    log.error("DEEPSEEK_API_KEY 或 ZHIPU_API_KEY 没设")
    log.error("先 cp .env.example .env，然后编辑 .env 填 2 个 key")
    log.error("DeepSeek: https://platform.deepseek.com/")
    log.error("智谱 GLM: https://bigmodel.cn/")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_CHAT_MODEL = "deepseek-chat"
ZHIPU_EMBEDDING_MODEL = "embedding-2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3


def load_docs():
    if not DATA_DIR.exists() or not any(DATA_DIR.iterdir()):
        log.error(f"没找到文档: {DATA_DIR}")
        log.error(f"先放几个 .txt 到 {DATA_DIR}")
        sys.exit(1)
    loader = DirectoryLoader(
        str(DATA_DIR), glob="**/*.txt", loader_cls=TextLoader
    )
    return loader.load()


def build_index(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    log.info(f"分成 {len(chunks)} 个 chunk")
    embeddings = ZhipuAIEmbeddings(
        model=ZHIPU_EMBEDDING_MODEL,
        api_key=ZHIPU_API_KEY,
    )
    index = FAISS.from_documents(chunks, embeddings)
    index.save_local(str(INDEX_DIR))
    return index, len(chunks)


def load_index():
    embeddings = ZhipuAIEmbeddings(
        model=ZHIPU_EMBEDDING_MODEL,
        api_key=ZHIPU_API_KEY,
    )
    return FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )


def make_qa(index):
    retriever = index.as_retriever(search_kwargs={"k": TOP_K})
    llm = ChatOpenAI(
        model=DEEPSEEK_CHAT_MODEL,
        temperature=0,
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY,
        timeout=120,
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
    )


def main():
    log.info(f"数据目录: {DATA_DIR}")
    log.info(f"索引目录: {INDEX_DIR}")

    # 1. Build or load index
    if (INDEX_DIR / "index.faiss").exists():
        log.info("发现已有索引, 直接加载...")
        index = load_index()
    else:
        log.info("建新索引...")
        docs = load_docs()
        log.info(f"加载 {len(docs)} 个文档")
        index, n_chunks = build_index(docs)
        n_docs = len(list(DATA_DIR.iterdir()))
        log.info(f"索引完成: {n_docs} 个文件 → {n_chunks} 个 chunk")

    # 2. Build QA chain
    qa = make_qa(index)

    # 3. Interactive Q&A loop
    print()
    print("=" * 60)
    print("  RAG demo ready (DeepSeek + ZhipuAI)")
    print("  输入问题按回车, 输入 quit / exit 退出")
    print("  示例: 解释 v5.5 跷跷板累积机制")
    print("=" * 60)
    print()

    while True:
        try:
            q = input("Q> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            log.info("退出")
            break
        if not q or q.lower() in ("quit", "exit"):
            log.info("退出")
            break
        try:
            result = qa.invoke({"query": q})
            print()
            print(f"A> {result['result']}")
            for i, doc in enumerate(result["source_documents"], 1):
                src = doc.metadata.get("source", "?")
                print(f"  [{i}] {src}")
            print()
        except Exception as e:
            log.error(f"调用失败: {e}")
            print()


if __name__ == "__main__":
    main()