# -*- coding: utf-8 -*-
"""
multi_query_rag.py — v0.1.11: Multi-Query Rewrite + Rerank

改进点 vs v0.1.10 (advanced_rag.py):
- query rewrite prompt 改成生成 3 个角度的查询 (用 ||| 分隔)
- 检索阶段: 对每个角度分别 top-3 检索, 合并去重
- rerank: BGE 重排合并后的 top-5 候选
- 适用场景: 多子问题 (如"X 是什么 + 多少度最佳"), 单查询召回不够
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
log = logging.getLogger("multi_query_rag")

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
TOP_K_PER_QUERY = 3
TOP_N_FINAL = 5

# --- prompts ---
MULTI_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是搜索查询优化助手. 把用户问题改写为 3 个不同角度的检索查询, "
               "用 ||| 分隔. 每个查询独立, 信息丰富, 用搜索友好的关键词."),
    ("human", "原问题: {question}\n3 个角度查询 (用 ||| 分隔):"),
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


def make_rewriter():
    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY, timeout=60,
    )
    return MULTI_QUERY_PROMPT | llm | StrOutputParser()


def make_reranker():
    return CrossEncoder(RERANKER_MODEL)


def retrieve_multi_query(index, query_str, top_k_per=TOP_K_PER_QUERY, top_n_final=TOP_N_FINAL, reranker=None):
    """解析 multi-query 字符串, 对每个角度分别检索, 合并去重, rerank."""
    queries = [q.strip() for q in query_str.split("|||") if q.strip()]
    log.info(f"[MultiQuery] 拆成 {len(queries)} 个子查询: {queries}")
    seen = set()
    candidates = []
    for q in queries:
        for doc in index.similarity_search(q, k=top_k_per):
            key = doc.page_content[:200]
            if key not in seen:
                seen.add(key)
                candidates.append(doc)
    log.info(f"[MultiQuery] 合并去重后 {len(candidates)} 个候选")
    if not reranker or len(candidates) <= top_n_final:
        return candidates[:top_n_final]
    pairs = [(queries[0], doc.page_content) for doc in candidates]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n_final]]


def make_multi_qa(index, rewriter, reranker, llm):
    def qa(question):
        rewritten = rewriter.invoke({"question": question})
        log.info(f"[MultiRewrite] {rewritten}")
        docs = retrieve_multi_query(index, rewritten, reranker=reranker)
        context = "\n\n---\n\n".join(f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs))
        answer = llm.invoke(ANSWER_PROMPT.format_messages(context=context, question=question))
        return answer.content, docs
    return qa


def main():
    log.info("初始化 Multi-Query RAG (v0.1.11)...")
    index, _n_docs, _n_chunks = build_or_load_index()
    rewriter = make_rewriter()
    reranker = make_reranker()
    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY, timeout=120,
    )
    qa = make_multi_qa(index, rewriter, reranker, llm)
    print()
    print("=" * 60)
    print("  Multi-Query RAG ready (v0.1.11)")
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