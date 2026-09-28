# -*- coding: utf-8 -*-
"""
app_streamlit.py — RAG + OCR 交互式 Web UI (Streamlit v2)

启动: streamlit run app_streamlit.py
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

# Streamlit Cloud secrets 同步到 os.environ
# (Cloud UI 的 Secrets 是 st.secrets, 不是 env vars; ultimate_rag.py 用 os.getenv 会拿不到)
try:
    import streamlit as st
    for _secret_key in ("DEEPSEEK_API_KEY", "ZHIPU_API_KEY"):
        if _secret_key in st.secrets and not os.environ.get(_secret_key):
            os.environ[_secret_key] = st.secrets[_secret_key]
except Exception:
    pass  # 非 Streamlit 运行环境 (本地 CLI) 跳过

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
        make_hyde_conservative_chain, make_reranker,
        make_ultimate_qa, make_ultimate_qa_stream,
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
        multi_chain = make_multi_query_chain(llm)
        hyde_chain = make_hyde_conservative_chain(llm)
        reranker = make_reranker()
        qa = make_ultimate_qa(idx, multi_chain, hyde_chain, reranker, llm)
        qa_stream = make_ultimate_qa_stream(idx, multi_chain, hyde_chain, reranker, llm)
    return idx, llm, qa, qa_stream


@st.cache_resource
def load_ocr():
    """懒加载 OCR 工具 (避免每次 rerun 重新 import)"""
    from agent import tool_zhipu_ocr
    return tool_zhipu_ocr


@st.cache_resource
def load_web_agent():
    """懒加载 Web Agent (ReAct + 8 tools: rag / ocr / bing / arxiv / wikipedia / github / search_all / fetch_url)"""
    from langchain_openai import ChatOpenAI
    from langchain.agents import create_agent
    from agent import (
        tool_rag_search, tool_zhipu_ocr, tool_search_web,
        tool_search_arxiv, tool_search_wikipedia, tool_search_github,
        tool_search_all, tool_fetch_url, SYSTEM_PROMPT,
    )

    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        timeout=120,
    )
    tools = [
        tool_rag_search,
        tool_zhipu_ocr,
        tool_search_web,
        tool_search_arxiv,
        tool_search_wikipedia,
        tool_search_github,
        tool_search_all,
        tool_fetch_url,
    ]
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        debug=False,
    )
    return agent


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
idx, llm, qa, qa_stream = load_rag()
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

    # v0.1.21: BYOK — 用户自带 API key, 免使用项目默认额度
    st.divider()
    st.header("🔑 自带 API Key (BYOK)")
    st.caption("填你自己的 key → 不消耗项目默认额度. 留空用默认. key 只存在本次 session.")
    user_ds = st.text_input("DeepSeek API Key", type="password", key="user_ds_key",
                              help="sk-... 开头. 在 platform.deepseek.com 申请")
    user_zp = st.text_input("智谱 API Key", type="password", key="user_zp_key",
                              help=".Zh... 格式. 在 open.bigmodel.cn 申请")
    if user_ds or user_zp:
        if user_ds:
            os.environ["DEEPSEEK_API_KEY"] = user_ds
        if user_zp:
            os.environ["ZHIPUAI_KEY"] = user_zp
            os.environ["ZHIPU_API_KEY"] = user_zp
        st.success("✅ 已切换到你的 key")
    else:
        st.info("ℹ️ 用项目默认 key (额度有限)")

    # v0.1.21: 累计成本 (session 内)
    if "cumulative_cost" not in st.session_state:
        st.session_state.cumulative_cost = 0.0
        st.session_state.cumulative_tokens_in = 0
        st.session_state.cumulative_tokens_out = 0
        st.session_state.cumulative_queries = 0

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

    # v0.1.21: 本次 session 累计用量
    st.divider()
    st.header("💰 本次 session 用量")
    # 存到 session_state 的 placeholder 引用, 主区查询完成后回填 (Streamlit sidebar 先渲染, 读到的是旧值)
    sb_q_ph = st.empty()
    sb_tok_ph = st.empty()
    sb_cost_ph = st.empty()
    sb_q_ph.metric("总查询数", st.session_state.get("cumulative_queries", 0))
    sb_tok_ph.metric("总 token (in/out)",
                     f"{st.session_state.get('cumulative_tokens_in', 0):,} / "
                     f"{st.session_state.get('cumulative_tokens_out', 0):,}")
    sb_cost_ph.metric("总费用估算", f"¥{st.session_state.get('cumulative_cost', 0):.4f}")
    st.session_state["_sb_placeholders"] = (sb_q_ph, sb_tok_ph, sb_cost_ph)
    if user_ds or user_zp:
        st.caption("✅ 用你自己的 key (不计费)")
    else:
        st.caption("⚠️ 用项目默认 key (按用量计费)")

    # v0.1.22: 付费订阅 (Cloudflare Worker + Stripe)
    st.divider()
    st.header("💎 Pro 订阅")
    from billing import is_billing_enabled
    if not is_billing_enabled():
        st.info("ℹ️ 订阅服务未部署 (BILLING_WORKER_URL 未配置)")
        st.caption("当前: 免费 10 次/天 或 填自己的 API Key 不限次")
    else:
        sub_email = st.text_input("Email (订阅管理)", key="sub_email",
                                    placeholder="your@email.com",
                                    help="订阅和 BYOK 都用这邮箱. 只存在 session.")
        if sub_email:
            from billing import check_subscription, create_checkout, create_portal
            sub = check_subscription(sub_email)
            status = sub.get("status", "none")
            # v0.1.23: 缓存 Pro 状态, 避免每次查询都打 Worker
            st.session_state.pro_status = status
            if status == "active":
                st.success("✅ Pro 订阅中")
                period_end = sub.get("current_period_end")
                if period_end:
                    import datetime as dt
                    end_date = dt.datetime.fromtimestamp(period_end).strftime("%Y-%m-%d")
                    st.caption(f"下次续费/到期: {end_date}")
                cust_id = sub.get("customer_id")
                if cust_id:
                    portal_url = create_portal(cust_id)
                    if portal_url and not portal_url.startswith("(error"):
                        st.markdown(f"[⚙️ 管理订阅]({portal_url})")
            else:
                st.info(f"ℹ️ 状态: {status} (免费: 每天 10 次)")
                checkout_url = create_checkout(sub_email)
                if checkout_url and not checkout_url.startswith("(error"):
                    st.markdown(f"[💎 升级 Pro]({checkout_url})")
                    st.caption("¥5/月 · 每天 100 次")
                else:
                    st.error(f"订阅服务连接失败: {checkout_url}")
        else:
            st.caption("填邮箱开通 Pro 订阅, 或下方填自己的 API Key")

    # v0.1.24: 每日 quota 显示 (Free 10 / Pro 100 / BYOK 不限)
    from quota import get_quota_status, PRO_DAILY_LIMIT
    pro_active = st.session_state.get("pro_status", "none") == "active"
    has_byok_now = bool(user_ds and user_zp)
    qs = get_quota_status(is_pro=pro_active)
    if has_byok_now:
        st.metric("🔑 今日查询", f"{qs['count']} (不限)")
        st.caption("BYOK: 用你自己的 key, 不限次不耗平台额度")
    elif pro_active:
        st.metric("💎 今日查询 (Pro)", f"{qs['count']} / {PRO_DAILY_LIMIT}")
        st.progress(min(qs['count'] / PRO_DAILY_LIMIT, 1.0))
        st.caption("¥5/月 · 每天 100 次 · 0 点重置")
    else:
        st.metric("今日查询 (免费)", f"{qs['count']} / {qs['limit']}")
        st.progress(min(qs['count'] / qs['limit'], 1.0))

# ---- 模式选择 ----
# 修复: 之前 st.session_state.mode = st.radio(...) 是双绑定写法
# Streamlit widget 读 st.session_state.mode_radio, 跟 st.session_state.mode 不对齐
# 第二次切模式会卡. 现在改成单向: widget 决定 mode, 再写回 session_state
if "mode" not in st.session_state:
    st.session_state.mode = "rag"
mode_index = {"rag": 0, "ocr": 1, "mm_rag": 2, "agent": 3}.get(st.session_state.mode, 0)
mode = st.radio(
    "🔀 模式",
    options=["rag", "ocr", "mm_rag", "agent"],
    index=mode_index,
    format_func=lambda x: {
        "rag":"🔍 RAG 检索", "ocr":"📷 纯 OCR",
        "mm_rag":"🖼️ OCR + 文档参考", "agent":"🤖 Web Agent"
    }[x],
    horizontal=True,
    key="mode_radio",
)
st.session_state.mode = mode

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

# ======================== 多模态 OCR + RAG 模式 ========================
elif st.session_state.mode == "mm_rag":
    st.subheader("🖼️ 多模态 OCR + 文档参考")
    st.caption("上传题图 → OCR 提题面 → RAG 找项目文档参考 → LLM 综合解答")

    mm_uploaded = st.file_uploader(
        "上传学生题目截图",
        type=["jpg", "jpeg", "png", "webp", "gif", "bmp"],
        key="mm_uploader",
    )

    mm_saved_path = None
    if mm_uploaded is not None:
        st.image(mm_uploaded, caption=mm_uploaded.name, width=400)
        tmp_dir = Path(tempfile.gettempdir()) / "raglab_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        mm_saved_path = tmp_dir / mm_uploaded.name
        mm_saved_path.write_bytes(mm_uploaded.getvalue())

    if st.button("🖼️ OCR + 文档参考 解答", type="primary", use_container_width=True):
        if mm_saved_path is None:
            st.error("❌ 请先上传图片")
        else:
            # v0.1.23: 限额检查
            from quota import check_can_query, increment_quota
            has_byok = bool(user_ds and user_zp)
            pro_status = st.session_state.get("pro_status", "none")
            is_pro = pro_status == "active"
            can, reason = check_can_query(has_byok, is_pro)
            if not can:
                st.error(f"🚫 {reason}")
                st.stop()

            st.divider()
            col_x, col_y = st.columns([4, 1])
            with col_x:
                st.markdown("### 🧠 综合解答")
            with col_y:
                # 单个 placeholder, 后续覆盖 (避免 st.metric 叠加渲染)
                mm_time_ph = st.empty()
                mm_time_ph.metric("⏱️ 用时", "streaming...")

            # v0.1.20: streaming — OCR + RAG 同步阻塞, LLM 综合这一步 stream
            try:
                t0 = time.time()
                from agent import tool_multimodal_solve_stream
                chunk_gen, sources, extracted_q = tool_multimodal_solve_stream(
                    str(mm_saved_path), qa
                )
                full_answer = st.write_stream(chunk_gen)
                elapsed = time.time() - t0

                # v0.1.21: 估算 mm_rag 成本 (OCR + RAG + 综合 LLM)
                # OCR 用 glm-4v (¥0.001/1K), RAG (DeepSeek + 智谱 embed), LLM (deepseek-chat)
                from ultimate_rag import calc_cost
                # 粗估: extracted_q 字符/2 + full_answer 字符/2 + RAG 上下文 + OCR image tokens ~1000
                char_count = len(extracted_q) + len(full_answer or "") + 5000  # RAG context 估算
                mm_usage = {
                    "llm_input_tokens": char_count // 2,
                    "llm_output_tokens": len(full_answer or "") // 2,
                    "embedding_tokens": 500,  # RAG 检索 3 query * 智谱 embed
                }
                mm_cost = calc_cost(mm_usage)
                # 加 OCR 单独计费 (glm-4v, ~¥0.001/1K tokens, 图片 ~1000 tokens)
                ocr_cost = 0.001
                total_cost = mm_cost + ocr_cost
                st.session_state.cumulative_cost += total_cost
                st.session_state.cumulative_queries += 1
            except Exception as e:
                st.error(f"❌ 多模态错误: {type(e).__name__}: {e}")
                st.stop()

            with col_y:
                mm_time_ph.metric("⏱️ 用时", f"{elapsed:.1f}s")
                mm_cost_ph = st.empty()
                mm_cost_ph.metric("💰 本次", f"¥{total_cost:.4f}")
                mm_src_ph = st.empty()
                mm_src_ph.metric("📚 文档", len(sources))

            if extracted_q:
                with st.expander("📋 OCR 提取的题面", expanded=False):
                    st.text(extracted_q)

            if sources:
                st.divider()
                st.markdown(f"### 📚 参考文档 ({len(sources)} 个)")
                for i, s in enumerate(sources, 1):
                    src_name = s.metadata.get("source", "?").split("\\")[-1]
                    with st.expander(f"[{i}] {src_name}", expanded=(i <= 3)):
                        st.caption(f"路径: {s.metadata.get('source', '?')}")
                        st.text(s.page_content[:800] + ("..." if len(s.page_content) > 800 else ""))

            st.download_button(
                "💾 下载解答",
                data=f"题面:\n{extracted_q}\n\n解答:\n{full_answer or ''}",
                file_name=f"mm_solve_{Path(mm_uploaded.name).stem}.txt",
                mime="text/plain",
            )


# ======================== Web Agent 模式 ========================
elif st.session_state.mode == "agent":
    st.subheader("🤖 Web Agent (ReAct)")
    st.caption("LLM 自动选工具: RAG / OCR / Web Search / URL Fetch")

    # 初始化 chat history
    if "agent_msgs" not in st.session_state:
        st.session_state.agent_msgs = []

    # 图片上传 (传给 OCR 工具)
    agent_img = st.file_uploader(
        "📷 可选: 上传图片供 OCR 工具调用",
        type=["jpg", "jpeg", "png", "webp", "gif", "bmp"],
        key="agent_uploader",
    )
    img_path = None
    if agent_img is not None:
        tmp_dir = Path(tempfile.gettempdir()) / "raglab_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        img_path = tmp_dir / agent_img.name
        img_path.write_bytes(agent_img.getvalue())
        st.image(agent_img, caption=agent_img.name, width=300)
        st.caption(f"💡 已上传图片, agent 看到时会自动调用 OCR. 路径: `{img_path}`")

    # 历史消息渲染
    for msg in st.session_state.agent_msgs:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])
        with st.chat_message(role):
            if content:
                st.markdown(content)
            if tool_calls:
                for tc in tool_calls:
                    with st.expander(f"🔧 调用工具: {tc.get('name', '?')}", expanded=False):
                        st.json(tc.get("args", {}))

    # 用户输入
    user_input = st.chat_input("💬 问 agent (中文)...", key="agent_input")
    if user_input:
        # 构造 user message, 如果有图片附加路径提示
        user_text = user_input
        if img_path:
            user_text += f"\n\n[系统提示: 用户上传了一张图片, 路径是 `{img_path}`, 调 zhipu_ocr 工具时传这个路径]"

        st.session_state.agent_msgs.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 调 agent
        agent = load_web_agent()
        try:
            with st.spinner("🤖 Agent 思考 + 调工具中... (最长 60s)"):
                t0 = time.time()
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": user_text}]},
                    config={"recursion_limit": 20},
                )
                elapsed = time.time() - t0

            # 提取所有消息 (包含 ai + tool)
            messages = result.get("messages", [])
            tool_calls_log = []
            final_answer = ""
            for m in messages:
                m_type = getattr(m, 'type', None) or (m.get('role') if isinstance(m, dict) else None)
                content = getattr(m, 'content', '') or (m.get('content') if isinstance(m, dict) else '')
                # 提取 tool_calls (LangChain 1.x: tool_calls 字段)
                tc = getattr(m, 'tool_calls', None) or []
                if tc and m_type == 'ai':
                    for t in tc:
                        tool_calls_log.append({
                            "name": getattr(t, 'name', '?') or t.get('name', '?'),
                            "args": getattr(t, 'args', {}) or t.get('args', {}),
                        })
                if m_type == 'ai' and content and not tc:
                    final_answer = content

            st.session_state.agent_msgs.append({
                "role": "assistant",
                "content": final_answer,
                "tool_calls": tool_calls_log,
                "elapsed": elapsed,
            })

            with st.chat_message("assistant"):
                if tool_calls_log:
                    for tc in tool_calls_log:
                        with st.expander(f"🔧 调了: {tc['name']}", expanded=False):
                            st.json(tc["args"])
                if final_answer:
                    st.markdown(final_answer)
                st.caption(f"⏱️ 用时 {elapsed:.1f}s")
        except Exception as e:
            st.error(f"❌ Agent 错误: {type(e).__name__}: {e}")

    # 清空按钮
    col1, _, _ = st.columns([1, 2, 4])
    with col1:
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.agent_msgs = []
            st.rerun()


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
        # v0.1.23: 限额检查 (BYOK / Pro 不限, Free 10/天)
        from quota import check_can_query, increment_quota, get_quota_status
        has_byok = bool(user_ds and user_zp)
        # Pro 状态从 session 拿, 没有就当 free
        pro_status = st.session_state.get("pro_status", "none")
        is_pro = pro_status == "active"
        can, reason = check_can_query(has_byok, is_pro)
        if not can:
            st.error(f"🚫 {reason}")
            st.info("👆 侧边栏填自己的 API key 或订阅 Pro 继续")
            st.stop()

        st.divider()
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown("### 💡 答案")
        with col_b:
            # 单个 placeholder, 后续用 .metric() 填内容 (避免 st.metric 叠加渲染)
            time_placeholder = st.empty()
            time_placeholder.metric("⏱️ 用时", "streaming...")

        # v0.1.20: streaming — LLM 输出逐 token 显示
        try:
            t0 = time.time()
            chunk_gen, sources, usage = qa_stream(question)
            # st.write_stream 自动边生成边刷新 UI
            full_answer = st.write_stream(chunk_gen)
            elapsed = time.time() - t0

            # v0.1.21: 累加 session 成本
            from ultimate_rag import calc_cost
            cost = calc_cost(usage)
            st.session_state.cumulative_cost += cost
            st.session_state.cumulative_tokens_in += usage.get("llm_input_tokens", 0)
            st.session_state.cumulative_tokens_out += usage.get("llm_output_tokens", 0)
            st.session_state.cumulative_queries += 1
            # v0.1.23: 免费用户 +1 计数 (BYOK / Pro 不计)
            if not has_byok and not is_pro:
                increment_quota()

            # 回填 sidebar 用量 (sidebar 先渲染, 必须用 placeholder 更新)
            _phs = st.session_state.get("_sb_placeholders")
            if _phs:
                _phs[0].metric("总查询数", st.session_state.cumulative_queries)
                _phs[1].metric("总 token (in/out)",
                               f"{st.session_state.cumulative_tokens_in:,} / "
                               f"{st.session_state.cumulative_tokens_out:,}")
                _phs[2].metric("总费用估算", f"¥{st.session_state.cumulative_cost:.4f}")
        except Exception as e:
            st.error(f"❌ RAG 错误: {type(e).__name__}: {e}")
            st.stop()

        # 更新用时 + 来源数 + 成本 (用同一个 placeholder 覆盖, 不再新开 col_b)
        with col_b:
            time_placeholder.metric("⏱️ 用时", f"{elapsed:.1f}s")
            cost_placeholder = st.empty()
            cost_placeholder.metric("💰 本次", f"¥{cost:.4f}")
            rag_src_ph = st.empty()
            rag_src_ph.metric("📚 Sources", len(sources))

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