# -*- coding: utf-8 -*-
"""
app_streamlit.py — RAG 交互式 Web UI (Streamlit)

启动: streamlit run D:\.minimax\.minimax\projects\llm-rag-lab\app_streamlit.py
默认: http://localhost:8501
"""
import os
import sys
import time
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 加载 .env (DEEPSEEK_API_KEY + ZHIPU_API_KEY)
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)

import streamlit as st

# ---- 配置 ----
TOP_N_FINAL = int(os.getenv("TOP_N_FINAL", "20"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "50000"))

# ---- 缓存 RAG 组件 (避免每次 rerun 重建) ----
@st.cache_resource
def load_rag():
    """启动时加载 RAG 组件, 缓存到 session"""
    from langchain_openai import ChatOpenAI
    from ultimate_rag import (
        build_or_load_index,
        make_multi_query_chain,
        make_hyde_conservative_chain,
        make_reranker,
        make_ultimate_qa,
    )

    if not os.environ.get("DEEPSEEK_API_KEY"):
        st.error("❌ .env 缺 DEEPSEEK_API_KEY")
        st.stop()
    if not os.environ.get("ZHIPU_API_KEY"):
        st.error("❌ .env 缺 ZHIPU_API_KEY")
        st.stop()

    with st.spinner("🔧 加载 RAG 组件 (BGE reranker + 索引 + LLM)..."):
        idx, n_docs, n_chunks = build_or_load_index()
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
    return idx, llm, qa, n_docs


# ---- 页面 ----
st.set_page_config(
    page_title="RAG Lab — 24306",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔍 RAG Lab — ZCR327/llm-rag-lab")
st.caption(f"DeepSeek 128K context × TopK={int(os.getenv('TOP_K_PER_QUERY', '8'))} × TopN={TOP_N_FINAL} × MaxCtxChars={MAX_CONTEXT_CHARS}")

# 加载
idx, llm, qa, n_docs = load_rag()
st.sidebar.success(f"✅ {n_docs} 文档就绪 (385 chunks)")

# ---- 侧边栏: 配置 + 示例问题 ----
with st.sidebar:
    st.header("⚙️ 配置")
    st.code(f"""TOP_N_FINAL={TOP_N_FINAL}
MAX_CONTEXT_CHARS={MAX_CONTEXT_CHARS}
TOP_K_PER_QUERY={int(os.getenv('TOP_K_PER_QUERY', '8'))}""", language="bash")
    st.caption("改 .env 调优 → 重启 Streamlit")

    st.divider()
    st.header("📝 示例问题")
    examples = [
        "BIOBUZZ 2026-2027 的核心元素是什么? HIVE 怎么算分?",
        "24306 机器人从 v2 到 v5 砍了什么? 为什么砍?",
        "Pedro Pathing 用什么算法? Bézier 怎么算?",
        "737 MAX 两次失事的共同技术原因是什么?",
        "v5.9 积分系统最近改了什么?",
        "智回社 HTTPS 怎么配置? 简要步骤",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{hash(ex)}", use_container_width=True):
            st.session_state.question = ex

    st.divider()
    st.header("📊 数据集统计")
    st.metric("文档数", n_docs)
    st.metric("chunk数 (chunks)", "385")
    st.metric("RAG 答对率 (11 题 benchmark)", "91%")

# ---- 主区: 输入 + 输出 ----
if "question" not in st.session_state:
    st.session_state.question = ""

question = st.text_area(
    "💬 你的问题",
    value=st.session_state.question,
    height=100,
    placeholder="例如: 24306 机器人从 v2 到 v5 砍了什么?",
)

col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    ask_btn = st.button("🚀 Ask RAG", type="primary", use_container_width=True)
with col2:
    clear_btn = st.button("🗑️ Clear", use_container_width=True)
if clear_btn:
    st.session_state.question = ""
    st.rerun()

if ask_btn and question.strip():
    with st.spinner(f"🔍 检索 + 生成中... (TopN={TOP_N_FINAL})"):
        t0 = time.time()
        try:
            answer, sources = qa(question)
            elapsed = time.time() - t0
        except Exception as e:
            st.error(f"❌ RAG 错误: {type(e).__name__}: {e}")
            st.stop()

    # ---- 显示答案 ----
    st.divider()
    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.markdown("### 💡 答案")
    with col_b:
        st.metric("⏱️ 用时", f"{elapsed:.1f}s")
        st.metric("📚 Sources", len(sources))

    st.markdown(answer)

    # ---- 显示 sources ----
    if sources:
        st.divider()
        st.markdown(f"### 📚 来源 ({len(sources)} 个)")
        for i, s in enumerate(sources, 1):
            src_name = s.metadata.get("source", "?").split("\\")[-1]
            with st.expander(f"[{i}] {src_name}", expanded=(i <= 3)):
                st.caption(f"路径: {s.metadata.get('source', '?')}")
                st.text(s.page_content[:800] + ("..." if len(s.page_content) > 800 else ""))

# ---- 底部: 文档列表 ----
with st.expander("📦 查看全部 56 文档"):
    raw_dir = Path(__file__).parent / "data" / "raw"
    docs = sorted([f.name for f in raw_dir.iterdir() if f.is_file()])
    for d in docs:
        st.markdown(f"- `{d}`")
    st.caption(f"共 {len(docs)} 文档 (gitignored, 本地)")

st.divider()
st.caption("v0.1.19 | 91% benchmark (10/11) | DeepSeek + 智谱 Embedding + BGE Reranker | 56 文档 / 385 chunks")