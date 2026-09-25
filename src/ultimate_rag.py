# -*- coding: utf-8 -*-
"""
ultimate_rag.py — v0.1.15: Multi-Query (2 angles) + Singleton BGE + Conservative HyDE

融合:
- v0.1.11 multi-query: 拆问题为多个角度查询 (v0.1.15 改 3→2 角度, 提速)
- v0.1.15 singleton: BGE reranker 模块级单例, 跨调用复用, 省 cold load 3-4s × N
- v0.1.12 hyde: LLM 生成假设答案
- v0.1.12 修复: hyde prompt 改成"保守版", 只描述涉及的领域术语, 不给具体数字/列表/定义
- v0.1.6 老实 prompt: 严格基于资料, 不编造

流程:
1. multi-query 改写 → 2 个角度查询 (v0.1.15: 3→2)
2. hyde 假设答案 (保守版, 只给领域术语) → 作为第 3 个查询
3. 对 3 个查询各检索 top-3 → 合并去重 → rerank top-3
4. LLM 用真实资料回答 (严格"不编造"prompt)
"""
import logging
import os
import sys
from pathlib import Path

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
log = logging.getLogger("ultimate_rag")

# --- config ---
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
# HF_ENDPOINT: 默认 huggingface.co (海外); 本地开发 .env 可设 hf-mirror.com 加速国内
if not os.environ.get("HF_ENDPOINT"):
    # 自动检测: 本地有 .env 用 hf-mirror, 部署到 Cloud 默认直连 HF
    if (ROOT / ".env").exists():
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not DEEPSEEK_API_KEY or not ZHIPU_API_KEY:
    log.error("DEEPSEEK_API_KEY 或 ZHIPU_API_KEY 没设")
    sys.exit(1)

DATA_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
# 默认从 HuggingFace Hub 拉 (BAAI/bge-reranker-base, ~278MB), Streamlit Cloud 自动下载
# 本地开发: .env 设 RERANKER_MODEL=D:\models\bge-reranker-base 走本地缓存
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
TOP_K_PER_QUERY = int(os.getenv("TOP_K_PER_QUERY", "8"))  # v0.1.19: 大上下文需要更多候选 (3 个 query × 8 = 24 candidates)
TOP_N_FINAL = int(os.getenv("TOP_N_FINAL", "20"))  # v0.1.19: 大上下文 (DeepSeek 128K / 4 tokens×1000chars=250/chunk → 20 chunks = 5K tokens = 上下文 ~5%)
# MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "50000"))  # 50K chars 上下文 (~12K tokens, DeepSeek 安全区)

# --- v0.1.15: BGE reranker 单例, 跨 tool_rag_search 调用复用 ---
_BGE_RERANKER = None

# --- prompts ---
MULTI_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是搜索查询优化助手. 把用户问题改写为 2 个不同角度的检索查询, "
               "用 ||| 分隔. 每个查询独立, 信息丰富, 用搜索友好的关键词."),
    ("human", "原问题: {question}\n2 个角度查询 (用 ||| 分隔):"),
])

# v0.1.14 关键改进: hyde 改成保守版, 不写具体内容, 只列可能涉及的领域术语
HYDE_CONSERVATIVE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是 RAG 系统的预检索器. 用户问问题, 你写一段 100-200 字的'领域术语清单', "
               "**只列出可能涉及的领域术语和概念** (5-10 个关键词/概念), "
               "**不要给具体数字、列表、定义、推导**. "
               "目的: 让 embedding 检索能命中相关文档, 不是给最终答案. "
               "如果完全不知道, 写'这个领域涉及 X、Y、Z 等相关概念'."),
    ("human", "问题: {question}\n涉及的领域术语 (5-10个):"),
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
    # v0.1.17: 加载 md + yaml + txt (智回社 logs 是 .txt code review)
    # LangChain DirectoryLoader 不支持 brace expansion, 用 **/*.* 通配
    loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.*",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        silent_errors=True,
    )
    docs = loader.load()
    # v0.1.18: 大 chunk_size 防跨版本对比 (Q2 v2→v5) 丢语义
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
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


def make_multi_query_chain(llm):
    return MULTI_QUERY_PROMPT | llm | StrOutputParser()


def make_hyde_conservative_chain(llm):
    return HYDE_CONSERVATIVE_PROMPT | llm | StrOutputParser()


def make_reranker():
    """v0.1.15: 返回 BGE reranker 单例. 跨 tool_rag_search 调用复用, 避免每次 cold load 3-4s."""
    global _BGE_RERANKER
    if _BGE_RERANKER is None:
        _BGE_RERANKER = CrossEncoder(RERANKER_MODEL)
    return _BGE_RERANKER


def retrieve_ultimate(index, queries, hyde_terms, reranker,
                     top_k_per=TOP_K_PER_QUERY, top_n_final=TOP_N_FINAL):
    """对 multi-query 2 角度 + hyde 术语合并检索 (v0.1.15: 3→2 角度)"""
    all_queries = [q.strip() for q in queries.split("|||") if q.strip()]
    # hyde 术语作为第 3 个查询 (单字符串, 整体检索)
    if hyde_terms and hyde_terms.strip():
        all_queries.append(hyde_terms.strip())
    log.info(f"[Ultimate] {len(all_queries)} 个查询 (2 multi-query + 1 hyde 术语)")
    seen = set()
    candidates = []
    for q in all_queries:
        for doc in index.similarity_search(q, k=top_k_per):
            key = doc.page_content[:200]
            if key not in seen:
                seen.add(key)
                candidates.append(doc)
    log.info(f"[Ultimate] 合并去重后 {len(candidates)} 个候选")
    if not reranker or len(candidates) <= top_n_final:
        return candidates[:top_n_final]
    # rerank (用第一个 query 作 anchor)
    pairs = [(all_queries[0], doc.page_content) for doc in candidates]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n_final]]


def make_ultimate_qa(index, multi_chain, hyde_chain, reranker, llm, max_context_chars=None):
    """v0.1.19: max_context_chars 控制总 context 长度 (默认 50000 = ~12K tokens, DeepSeek 安全区)
    DeepSeek 128K tokens 上限, 我们用 ~5% 作为 context, 留 95% 给 model 思考"""
    if max_context_chars is None:
        max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "50000"))

    def qa(question):
        # 1. multi-query 拆 2 角度 (v0.1.15: 3→2, 提速)
        multi_str = multi_chain.invoke({"question": question})
        log.info(f"[MultiRewrite] {multi_str}")

        # 2. hyde 保守版 (只列术语)
        hyde_terms = hyde_chain.invoke({"question": question})
        log.info(f"[HyDE 保守] {hyde_terms[:100]}")

        # 3. 合并检索
        docs = retrieve_ultimate(index, multi_str, hyde_terms, reranker)
        # 4. 拼 context 但不超 max_context_chars
        parts = []
        total = 0
        for i, doc in enumerate(docs):
            chunk = f"[{i+1}] {doc.page_content}"
            if total + len(chunk) > max_context_chars:
                log.info(f"[Context] 截断 at {i} chunks, {total} chars")
                break
            parts.append(chunk)
            total += len(chunk)
        context = "\n\n---\n\n".join(parts)
        log.info(f"[Context] {len(parts)} chunks, {total} chars (~{total//4} tokens)")

        # 5. LLM 回答 (v0.1.6 老实 prompt)
        answer = llm.invoke(ANSWER_PROMPT.format_messages(context=context, question=question))
        return answer.content, docs
    return qa


def main():
    log.info("初始化 Ultimate RAG (v0.1.14)...")
    index, _n_docs, _n_chunks = build_or_load_index()
    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY, timeout=120,
    )
    multi_chain = make_multi_query_chain(llm)
    hyde_chain = make_hyde_conservative_chain(llm)
    reranker = make_reranker()
    qa = make_ultimate_qa(index, multi_chain, hyde_chain, reranker, llm)
    print()
    print("=" * 60)
    print("  Ultimate RAG ready (v0.1.15)")
    print("  multi-query (2 角度) + hyde 保守 (只列术语) + BGE 单例 + rerank")
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