# -*- coding: utf-8 -*-
"""
app_streamlit.py — RAG + OCR 交互式 Web UI (Streamlit v2)

启动: streamlit run D:\.minimax\.minimax\projects\llm-rag-lab\app_streamlit.py
默认: http://localhost:8501

v2 新增:
- 上传图片 → 智谱 GLM-4V OCR (extract 或 solve 模式)
- 切换 RAG / OCR 模式
- 图片预览缩略图
"""
import os
import sys
import time
import shutil
import tempfile
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 把 src/ 加到 sys.path (Streamlit 不会自动加)
SRC_DIR = Path(__file__).parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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
    from langchain_openai import ChatOpenAI
    from ultimate_rag import (
        build_or_load_index, make_multi_query_chain,
        make_hyde_conservative_chain, make_reranker, make_ultimate_qa,
    )

    if not os.environ.get("DEEPSEEK_API_KEY"):
        st.error("❌ .env 缺 DEEPSEEK_API_KEY"); st.stop()
    if not os.environ.get("ZHIPU_API_KEY"):
        st.error("❌ .env 缺 ZHIPU_API_KEY"); st.stop()

    with st.spinner("🔧 加载 RAG 组件 (BGE reranker + 索引 + LLM)..."):
        idx, _, _ = build_or_load_index()
        llm = ChatOpenAI(
            model="deepseek-chat", temperature=0,
            base_url="https://api.deepseek.com/v1",
            api_key=os.environ["DEEPSEEK_API_KEY"],
            timeout=120,
        )
        qa = make_ultimate_qa(
            idx, make_multi_query_chain(llm),
            make_hyde_conservative_chain(llm), make_reranker(), llm,
        )
    return idx, llm, qa


@st.cache_resource
def load_ocr():
    """懒加载 OCR 工具 (避免每次 rerun 重新 import)"""
    from agent import tool_zhipu_ocr
    return tool_zhipu_ocr


# ---- 页面 ----
st.set_page_config(
    page_title="RAG Lab — 24306",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔍 RAG Lab — ZCR327/llm-rag-lab")
st.caption(f"DeepSeek 128K × TopK={int(os.getenv('TOP_K_PER_QUERY', '8'))} × TopN={TOP_N_FINAL} × MaxCtxChars={MAX_CONTEXT_CHARS} | + 智谱 GLM-4V OCR")

# 加载
idx, llm, qa = load_rag()
ocr_func = load_ocr()
n_docs = len(list((Path(__file__).parent / "data" / "raw").iterdir()))

st.sidebar.success(f"✅ {n_docs} 文档就绪 (385 chunks)")

# ---- 侧边栏 ----
with st.sidebar:
    st.header("⚙️ 配置")
    st.code(f"""TOP_N_FINAL={TOP_N_FINAL}
MAX_CONTEXT_CHARS={MAX_CONTEXT_CHARS}
TOP_K_PER_QUERY={int(os.getenv('TOP_K_PER_QUERY', '8'))}""", language="bash")
    st.caption("改 .env 调优 → 重启 Streamlit")

    st.divider()
    st.header("📝 示例问题 (RAG)")
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
            st.session_state.uploaded_img = None

    st.divider()
    st.header("📊 数据集统计")
    st.metric("文档数", n_docs)
    st.metric("chunk数 (chunks)", "385")
    st.metric("RAG 答对率 (11 题 benchmark)", "91%")

# ---- 模式选择 ----
if "mode" not in st.session_state:
    st.session_state.mode = "rag"  # rag 或 ocr
st.session_state.mode = st.radio(
    "🔀 模式",
    options=["rag", "ocr"],
    format_func=lambda x: "🔍 RAG 检索" if x == "rag" else "📷 OCR 题目截图",
    horizontal=True,
    key="mode_radio",
)

st.divider()

# ---- 主区 ----
if "question" not in st.session_state:
    st.session_state.question = ""

# ======================== OCR 模式 ========================
if st.session_state.mode == "ocr":
    st.subheader("📷 智谱 GLM-4V 多模态 OCR")
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        uploaded = st.file_uploader(
            "上传学生题目截图 (jpg/png/webp/gif/bmp)",
            type=["jpg", "jpeg", "png", "webp", "gif", "bmp"],
            key="ocr_uploader",
        )
    with col_u2:
        ocr_mode = st.radio(
            "模式",
            options=["extract", "solve"],
            format_func=lambda x: {"extract":"📝 纯 OCR", "solve":"🧠 OCR+解题"}[x],
            horizontal=False,
            key="ocr_mode_radio",
        )

    saved_path = None
    if uploaded is not None:
        # 显示预览
        st.image(uploaded, caption=uploaded.name, width=400)
        # 保存到临时文件
        tmp_dir = Path(tempfile.gettempdir()) / "raglab_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        saved_path = tmp_dir / uploaded.name
        saved_path.write_bytes(uploaded.getvalue())

    custom_q = st.text_input(
        "💬 附加提示 (可选, 比如 '用 LaTeX 格式' 或 '解第 2 题')",
        key="ocr_custom_q",
        placeholder="留空用默认提示词",
    )

    col_r1, col_r2 = st.columns([1, 5])
    with col_r1:
        run_ocr = st.button("📷 跑 OCR", type="primary", use_container_width=True)

    if run_ocr:
        if saved_path is None:
            st.error("❌ 请先上传图片")
        else:
            with st.spinner(f"🤖 智谱 GLM-4V 处理中... (模式: {ocr_mode})"):
                t0 = time.time()
                result = ocr_func(str(saved_path), mode=ocr_mode)
                elapsed = time.time() - t0
            st.divider()
            col_x, col_y = st.columns([4, 1])
            with col_x:
                st.markdown(f"### {'📝 提取' if ocr_mode=='extract' else '🧠 解答'}")
            with col_y:
                st.metric("⏱️ 用时", f"{elapsed:.1f}s")
            st.markdown(f"```\n{result}\n```")
            if custom_q:
                st.caption(f"附加提示: {custom_q}")
            st.download_button(
                "💾 下载结果",
                data=result,
                file_name=f"ocr_{ocr_mode}_{Path(uploaded.name).stem}.txt",
                mime="text/plain",
            )

# ======================== RAG 模式 ========================
else:
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

        st.divider()
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown("### 💡 答案")
        with col_b:
            st.metric("⏱️ 用时", f"{elapsed:.1f}s")
            st.metric("📚 Sources", len(sources))

        st.markdown(answer)

        if sources:
            st.divider()
            st.markdown(f"### 📚 来源 ({len(sources)} 个)")
            for i, s in enumerate(sources, 1):
                src_name = s.metadata.get("source", "?").split("\\")[-1]
                with st.expander(f"[{i}] {src_name}", expanded=(i <= 3)):
                    st.caption(f"路径: {s.metadata.get('source', '?')}")
                    st.text(s.page_content[:800] + ("..." if len(s.page_content) > 800 else ""))

# ---- 底部: 文档列表 ----
with st.expander(f"📦 查看全部 {n_docs} 文档"):
    raw_dir = Path(__file__).parent / "data" / "raw"
    docs = sorted([f.name for f in raw_dir.iterdir() if f.is_file()])
    for d in docs:
        st.markdown(f"- `{d}`")
    st.caption(f"共 {len(docs)} 文档 (gitignored, 本地)")

st.divider()
st.caption("v0.1.19 + OCR | 91% benchmark (10/11) | DeepSeek + 智谱 Embedding + BGE Reranker + 智谱 GLM-4V OCR | 56 文档 / 385 chunks")