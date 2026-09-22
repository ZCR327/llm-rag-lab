# -*- coding: utf-8 -*-
"""
advanced_rag.py — Phase 1 Week 4+ Advanced RAG
- Query Rewriting: DeepSeek 把模糊问题改写为更精确的检索查询
- Re-ranking: BGE-reranker-base 本地 cross-encoder, 对初检 top-10 重排成 top-3

对比 minimal_rag.py (v0.1.3) 应该有:
- 更准的 top-1 答案 (rerank)
- 更全的覆盖 (query rewrite)
- 多 2-3 秒延迟 (1 次 rewrite + 1 次 reranker)
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("advanced_rag")

# --- config ---
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# 国内访问 HuggingFace 不稳, 默认走 hf-mirror 镜像
# 强制赋值 (setdefault 时机不可靠)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not DEEPSEEK_API_KEY or not ZHIPU_API_KEY:
    log.error("DEEPSEEK_API_KEY 或 ZHIPU_API_KEY 没设")
    sys.exit(1)

DATA_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

RERANKER_MODEL = "BAAI/bge-reranker-base"
INITIAL_K = 10  # 初检多取
FINAL_N = 3    # rerank 后保留

# --- prompts ---
QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个搜索查询优化助手. 把用户的问题改写为更精确、信息更丰富的检索查询. "
               "只输出改写后的查询, 不要加任何前缀或解释."),
    ("human", "原问题: {question}\n改写后:"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个基于参考资料回答问题的助手. 如果资料不包含答案, 老实说不知道. "
               "回答简洁, 用中文."),
    ("human", "参考资料:\n{context}\n\n问题: {question}\n\n答案:"),
])


def build_or_load_index():
    if (INDEX_DIR / "index.faiss").exists():
        log.info("加载已有 FAISS 索引...")
        embeddings = ZhipuAIEmbeddings(model="embedding-2", api_key=ZHIPU_API_KEY)
        return FAISS.load_local(
            str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
        )
    log.info("建新索引 (首次会慢)...")
    loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    log.info(f"分成 {len(chunks)} 个 chunk")
    embeddings = ZhipuAIEmbeddings(model="embedding-2", api_key=ZHIPU_API_KEY)
    index = FAISS.from_documents(chunks, embeddings)
    index.save_local(str(INDEX_DIR))
    return index


def make_query_rewriter():
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        timeout=60,
    )
    return QUERY_REWRITE_PROMPT | llm | StrOutputParser()


def make_reranker():
    log.info(f"加载 reranker: {RERANKER_MODEL} (首次会下载 ~100MB)...")
    return CrossEncoder(RERANKER_MODEL)


def retrieve_with_rerank(index, query, reranker, top_k=INITIAL_K, top_n=FINAL_N):
    """初检 top_k + rerank 选 top_n"""
    candidates = index.similarity_search(query, k=top_k)
    if not reranker or len(candidates) <= top_n:
        return candidates
    pairs = [(query, doc.page_content) for doc in candidates]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [doc for score, doc in ranked[:top_n]]


def make_advanced_qa(index, rewriter, reranker, llm):
    """组合: rewrite -> retrieve+rerank -> answer"""
    def advanced_qa(question):
        # 1. Query rewrite
        rewritten = rewriter.invoke({"question": question})
        log.info(f"[Rewrite] {rewritten}")

        # 2. Retrieve + rerank
        docs = retrieve_with_rerank(index, rewritten, reranker=reranker)
        context = "\n\n---\n\n".join(
            f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs)
        )

        # 3. Generate answer
        answer = llm.invoke(
            ANSWER_PROMPT.format_messages(context=context, question=question)
        )
        return answer.content, docs

    return advanced_qa


def main():
    log.info("初始化 Advanced RAG...")
    index = build_or_load_index()
    rewriter = make_query_rewriter()
    reranker = make_reranker()
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        timeout=120,
    )
    qa = make_advanced_qa(index, rewriter, reranker, llm)

    print()
    print("=" * 60)
    print("  Advanced RAG ready (DeepSeek rewrite + BGE rerank)")
    print("  输入问题按回车, 输入 quit/exit 退出")
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
                src = doc.metadata.get("source", "?")
                print(f"  [{i}] {src}")
            print()
        except Exception as e:
            log.error(f"调用失败: {e}")


if __name__ == "__main__":
    main()