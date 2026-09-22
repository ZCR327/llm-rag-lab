# -*- coding: utf-8 -*-
"""
hyde_rag.py — v0.1.12: HyDE (Hypothetical Document Embeddings)

改进点 vs v0.1.10 (advanced_rag.py):
- LLM 先生成 100-200 字"假设答案"
- 用假设答案 (而不是用户原始问题) embedding 去检索
- 原因: 假设答案比短查询更长 + 含技术术语, 跟文档的 embedding 空间更接近
- rerank top-3 + 老实 prompt
"""
import logging
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
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import CrossEncoder

import faiss
import numpy as np
from langchain_community.docstore.in_memory import InMemoryDocstore
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hyde_rag")

# --- config ---
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not DEEPSEEK_API_KEY or not ZHIPU_API_KEY:
    log.error("DEEPSEEK_API_KEY 或 ZHIPU_API_KEY 没设")
    sys.exit(1)

DATA_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
RERANKER_MODEL = str(ROOT / "models" / "bge-reranker-base")
INITIAL_K = 10
FINAL_N = 3

# --- prompts ---
HYDE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是该领域专家. 用户问问题, 你先写一段 100-200 字的'假设答案', "
               "用可能含技术术语的语言回答, 即便不确定. "
               "不要加'我不知道'之类的前缀, 直接写答案."),
    ("human", "问题: {question}\n假设答案 (100-200字):"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是基于参考资料回答问题的助手. "
               "**严格基于参考资料**回答. 如果资料里没有明确说某个事实, "
               "必须老实说'不知道'或'资料未提供', "
               "**绝对不要编造**未在资料中出现的物理原理、数字、原因、推导. "
               "回答简洁, 用中文."),
    ("human", "参考资料:\n{context}\n\n问题: {question}\n\n答案:"),
])


def build_or_load_index():
    """Build or load index. Returns (index, n_docs, n_chunks)."""
    if (INDEX_DIR / "index.faiss").exists():
        log.info("加载已有 FAISS 索引...")
        embeddings = ZhipuAIEmbeddings(model="embedding-2", api_key=ZHIPU_API_KEY)
        index = FAISS.load_local(
            str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
        )
        n_docs = len(list(DATA_DIR.iterdir()))
        return index, n_docs, 0
    log.info("建新索引...")
    loader = DirectoryLoader(
        str(DATA_DIR), glob="**/*.md", loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    log.info(f"分成 {len(chunks)} 个 chunk")
    BATCH_SIZE = 6
    embeddings = ZhipuAIEmbeddings(model="embedding-2", api_key=ZHIPU_API_KEY)
    all_vectors = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_texts = [c.page_content for c in batch]
        all_vectors.extend(embeddings.embed_documents(batch_texts))
    vectors_np = np.array(all_vectors, dtype=np.float32)
    faiss_index = faiss.IndexFlatL2(vectors_np.shape[1])
    faiss_index.add(vectors_np)
    chunk_ids = [str(uuid4()) for _ in range(len(chunks))]
    docstore = InMemoryDocstore({cid: doc for cid, doc in zip(chunk_ids, chunks)})
    index_to_docstore_id = {i: cid for i, cid in enumerate(chunk_ids)}
    from langchain_community.vectorstores.faiss import FAISS as FAISSClass
    index = FAISSClass(
        embedding_function=embeddings,
        index=faiss_index, docstore=docstore, index_to_docstore_id=index_to_docstore_id,
    )
    index.save_local(str(INDEX_DIR))
    return index, len(docs), len(chunks)


def make_hyde_chain():
    """HyDE chain: question -> hypothesis (LLM) -> hypothesis string"""
    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0.5,  # 高一些让假设有变化
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY, timeout=60,
    )
    return HYDE_PROMPT | llm | StrOutputParser()


def make_reranker():
    return CrossEncoder(RERANKER_MODEL)


def retrieve_with_rerank(index, query, reranker, top_k=INITIAL_K, top_n=FINAL_N):
    candidates = index.similarity_search(query, k=top_k)
    if not reranker or len(candidates) <= top_n:
        return candidates
    pairs = [(query, doc.page_content) for doc in candidates]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n]]


def make_hyde_qa(index, hyde_chain, reranker, llm):
    def qa(question):
        # 1. LLM 生成假设答案
        hypothesis = hyde_chain.invoke({"question": question})
        log.info(f"[HyDE] 假设答案: {hypothesis[:100]}...")

        # 2. 用假设答案去检索 (而不是用问题)
        docs = retrieve_with_rerank(index, hypothesis, reranker=reranker)
        context = "\n\n---\n\n".join(f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs))

        # 3. 用检索到的资料回答原问题
        answer = llm.invoke(ANSWER_PROMPT.format_messages(context=context, question=question))
        return answer.content, docs
    return qa


def main():
    log.info("初始化 HyDE RAG (v0.1.12)...")
    index, _n_docs, _n_chunks = build_or_load_index()
    hyde_chain = make_hyde_chain()
    reranker = make_reranker()
    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY, timeout=120,
    )
    qa = make_hyde_qa(index, hyde_chain, reranker, llm)
    print()
    print("=" * 60)
    print("  HyDE RAG ready (v0.1.12)")
    print("=" * 60)
    print()
    while True:
        try:
            q = input("Q> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("quit", "exit"):
            break
        try:
            answer, sources = qa(q)
            print(f"\nA> {answer}")
            for i, doc in enumerate(sources, 1):
                print(f"  [{i}] {doc.metadata.get('source', '?').split(chr(92))[-1]}")
            print()
        except Exception as e:
            log.error(f"调用失败: {e}")


if __name__ == "__main__":
    main()