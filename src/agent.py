# -*- coding: utf-8 -*-
"""
agent.py — Web Agent (Phase 2) 加在 RAG 仓库 (v0.1.16)

基于 v0.1.15 ultimate_rag (multi-query 2 angles + BGE rerank singleton + hyde-conservative)
加 3 个 tool:
- rag_search: **优先调用**, 覆盖本地 5 FTC + 1 飞机文档 (qa closure 单例, 跨调用复用)
- search_web: cn.bing.com HTML 爬 (主, 直连, 免 key) + Brave API (opt) + DDG (last fallback)
- fetch_url: 抓取 + 提取正文 (httpx + BS4)

使用 LangChain v1.0 新 API: from langchain.agents import create_agent
- system_prompt 引导工具优先级 + 收敛策略
- recursion_limit=20 防止无限循环

性能:
- v0.1.14: 单题 27s (每次重建 LLM + chains + qa)
- v0.1.15 (singleton BGE): 单题 16-25s
- v0.1.16 (qa 单例): 期望 ≤10s (实测待验证)

Usage:
    # 装包: pip install -U langchain langgraph beautifulsoup4 httpx python-dotenv (清华源)
    # v0.1.17+: agent.py 自动从 .env 加载, 不需要手动 export
    # (可选) $env:BRAVE_API_KEY = "BSA..." 切换 Brave Search API (国外)
    # 跑: python D:\.minimax\.minimax\projects\llm-rag-lab\src\agent.py
"""
import os
import sys
import re
import time
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# v0.1.17: 自动从项目根 .env 加载 (DEEPSEEK_API_KEY / ZHIPU_API_KEY 等)
# 避免每次跑前手动 source .env
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)  # 不覆盖已有 env var
except ImportError:
    pass  # dotenv 未装时退到 os.environ

# 国内 hf-mirror 镜像 (跟其他 RAG 脚本一致)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 真实浏览器 User-Agent (cn.bing.com 对 UA 很严, 假的会被 PoW challenge 拦)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ======================== Search backends ========================

def _search_bing_cn(query: str, num_results: int) -> str:
    """cn.bing.com HTML 爬取 - 国内直连, 免 key, 首选

    result block: <li class="b_algo">
      <h2><a href="..." target="_blank">title</a></h2>
      <div class="b_caption"><p class="b_lineclamp2">snippet</p></div>
    """
    import httpx
    from bs4 import BeautifulSoup
    r = httpx.get(
        "https://cn.bing.com/search",
        params={"q": query, "FORM": "QBRE", "setlang": "zh-CN"},
        headers={"User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9"},
        timeout=15.0,
        follow_redirects=True,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 a")
        if not a:
            continue
        url = a.get("href", "")
        title = a.get_text(strip=True)
        cap = li.select_one(".b_caption p")
        snippet = cap.get_text(" ", strip=True) if cap else ""
        # 跳过 bing 内部跳转
        if not url.startswith("http"):
            continue
        results.append(f"[{len(results)+1}] {title}\n    URL: {url}\n    {snippet}")
        if len(results) >= num_results:
            break
    if not results:
        raise RuntimeError("cn.bing returned no li.b_algo (可能触发 PoW 或区域限制)")
    return "\n\n".join(results)


def _search_brave(query: str, num_results: int, api_key: str) -> str:
    """Brave Search API - 国外, 需 BRAVE_API_KEY, 2000 q/月免费"""
    import httpx
    r = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": num_results},
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        timeout=15.0,
    )
    r.raise_for_status()
    data = r.json()
    results = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            f"[{len(results)+1}] {item.get('title', '')}\n"
            f"    URL: {item.get('url', '')}\n"
            f"    {item.get('description', '')}"
        )
        if len(results) >= num_results:
            break
    if not results:
        raise RuntimeError("Brave returned empty results")
    return "\n\n".join(results)


def _search_ddg(query: str, num_results: int) -> str:
    """DuckDuckGo Lite/HTML - 最后 fallback (国内经常 GFW 屏蔽)"""
    import httpx
    for url, tag in [
        ("https://lite.duckduckgo.com/lite/", "lite"),
        ("https://html.duckduckgo.com/html/", "html"),
    ]:
        try:
            r = httpx.get(
                url,
                params={"q": query, "kl": "us-en"},
                headers={"User-Agent": _UA},
                timeout=15.0,
            )
            r.raise_for_status()
            html = r.text
            results = []
            if tag == "lite":
                pattern = (
                    r'<a[^>]+href="([^"]+)"[^>]*class="result-link"[^>]*>.*?</a>.*?'
                    r'class="result-snippet"[^>]*>(.*?)</td>'
                )
            else:
                pattern = (
                    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?'
                    r'class="result__snippet"[^>]*>(.*?)</a>'
                )
            for m in re.finditer(pattern, html, re.DOTALL):
                if tag == "lite":
                    url_link, snippet = m.group(1), m.group(2).strip()
                    title = ""
                else:
                    url_link, title, snippet = m.group(1), m.group(2).strip(), m.group(3).strip()
                snippet = re.sub(r"<[^>]+>", "", snippet).strip()
                if not url_link.startswith("http"):
                    continue
                results.append(
                    f"[{len(results)+1}] {title}\n"
                    f"    URL: {url_link}\n"
                    f"    {snippet}"
                )
                if len(results) >= num_results:
                    break
            if results:
                return "\n\n".join(results)
        except Exception:
            continue
    raise RuntimeError("DDG both endpoints failed")


# ======================== Tools ========================

# v0.1.16: module-level cache for qa closure - 跨 tool_rag_search 调用复用
# 省 ~1-2s/次 (ChatOpenAI 初始化 + chain 构造 + reranker load)
_QA_CACHE = None


def _get_qa():
    """获取 (qa 闭包, index) 单例, 首次调用构造, 后续复用. 与 make_reranker 单例叠加效果."""
    global _QA_CACHE
    if _QA_CACHE is None:
        from ultimate_rag import (
            build_or_load_index,
            make_multi_query_chain,
            make_hyde_conservative_chain,
            make_reranker,
            make_ultimate_qa,
        )
        from langchain_openai import ChatOpenAI

        index, _, _ = build_or_load_index()
        llm = ChatOpenAI(
            model="deepseek-chat", temperature=0,
            base_url="https://api.deepseek.com/v1",
            api_key=os.environ["DEEPSEEK_API_KEY"],
            timeout=120,
        )
        multi_chain = make_multi_query_chain(llm)
        hyde_chain = make_hyde_conservative_chain(llm)
        reranker = make_reranker()  # 内部也是单例
        qa = make_ultimate_qa(index, multi_chain, hyde_chain, reranker, llm)
        _QA_CACHE = qa
    return _QA_CACHE


def tool_rag_search(query: str) -> str:
    """**优先调用** - 查本地 6 文档 (5 FTC + 1 飞机), 4-6 秒返回. 覆盖:
    - FTC V0.9 游戏规则 (DECODE / SKYSTONE / POWERPLAY / ULTIMATE GOAL / 等)
    - FTC 机器人技术 (Pedro Pathing, 路径规划, 计算机视觉, 自动驾驶)
    - FTC 比赛策略 (联盟选择, AUTO/TELEOP, 翻 HIVE, 投 POLLEN 等)
    - 飞机 (737 MAX) 事故分析 (MCAS 失事案例)

    返回: 答案 (中文) + 来源文件列表
    **如果本地 RAG 给了答案就直接用**, 不要再 search_web (本工具已包含 multi-query + rerank)
    """
    try:
        qa = _get_qa()  # 单例, 跨调用复用
        answer, sources = qa(query)
        src_list = "\n".join(
            f"  [{i+1}] {s.metadata.get('source', '?').split(chr(92))[-1]}"
            for i, s in enumerate(sources)
        )
        return f"本地 RAG 答案:\n{answer}\n\n来源:\n{src_list}"
    except Exception as e:
        return f"(RAG error: {e})"


def tool_search_web(query: str, num_results: int = 5) -> str:
    """网页搜索 (本地 RAG 没答案时再用), 适合查最新信息或找网页来源.

    优先级:
      1. cn.bing.com HTML 爬 (国内直连, 免 key) - 首选
      2. Brave Search API (国外, 需 BRAVE_API_KEY 环境变量) - 可选
      3. DuckDuckGo Lite/HTML (国内经常 GFW 屏蔽) - 最后兜底

    返回: 编号结果列表, 每个含 title + URL + snippet
    """
    # 1. cn.bing.com HTML (国内直连)
    try:
        return _search_bing_cn(query, num_results)
    except Exception as e1:
        last_err = f"cn.bing: {type(e1).__name__}: {str(e1)[:80]}"
    # 2. Brave Search API (国外, opt)
    brave_key = os.environ.get("BRAVE_API_KEY")
    if brave_key:
        try:
            return _search_brave(query, num_results, brave_key)
        except Exception as e2:
            last_err += f" | brave: {type(e2).__name__}: {str(e2)[:80]}"
    # 3. DuckDuckGo (last)
    try:
        return _search_ddg(query, num_results)
    except Exception as e3:
        last_err += f" | ddg: {type(e3).__name__}: {str(e3)[:80]}"
    return f"(search failed for all endpoints, query: {query}, errors: {last_err})"


def tool_fetch_url(url: str, max_chars: int = 3000) -> str:
    """抓取 URL, 提取正文 (去 HTML 标签, 留文字)

    适合: search_web 拿到 URL 后深入读
    """
    import httpx
    from bs4 import BeautifulSoup
    try:
        r = httpx.get(
            url,
            headers={"User-Agent": _UA},
            timeout=20.0,
            follow_redirects=True,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # 去 script/style
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # 截断
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        return f"URL: {url}\n\n{text}"
    except Exception as e:
        return f"(fetch error: {e})"


def tool_zhipu_ocr(image_path: str, mode: str = "extract") -> str:
    """**学生题目截图 OCR** - 智谱 GLM-4V 多模态 (替代 PaddlePaddle/EasyOCR/jina).

    适合: 学生数学题 / 物理题 / 化学题截图, 需要公式识别 (LaTeX 输出).

    参数:
      image_path: 图片绝对路径 (jpg/png/webp/gif/bmp)
      mode: 'extract' (纯 OCR, 公式用 LaTeX) 或 'solve' (OCR + 完整解答)

    返回: 提取的文本/解答 (中文)

    失败回退: PaddlePaddle (Intel Iris Xe 不稳) / jina-ocr-v1 本地 (慢, 公式弱)
    """
    import base64
    import mimetypes
    from pathlib import Path as _Path

    api_key = os.environ.get("ZHIPUAI_KEY") or os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        return "(zhipu_ocr error: 缺 ZHIPUAI_KEY / ZHIPU_API_KEY)"

    img_path = _Path(image_path)
    if not img_path.exists():
        return f"(zhipu_ocr error: 图片不存在 {image_path})"

    if mode not in ("extract", "solve"):
        return f"(zhipu_ocr error: mode 必须是 extract/solve, 收到 {mode!r})"

    # 图片压缩: 智谱 GLM-4V 拒收 >4MB base64 / 太大图片, 自动 resize 到 1600px 长边 + JPEG 92%
    img_bytes = img_path.read_bytes()
    if len(img_bytes) > 2_000_000:  # 2MB 阈值
        try:
            from io import BytesIO
            from PIL import Image
            with Image.open(img_path) as im:
                # 长边缩到 1600px (智谱 vision 模型常见上限)
                im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                buf = BytesIO()
                im = im.convert("RGB") if im.mode in ("RGBA", "LA", "P") else im
                im.save(buf, format="JPEG", quality=92)
                img_bytes = buf.getvalue()
                mime = "image/jpeg"
        except Exception as e:
            return f"(zhipu_ocr error: 图片压缩失败 ({type(e).__name__}: {e}))"
    else:
        mime, _ = mimetypes.guess_type(str(img_path))
        if mime is None:
            ext = img_path.suffix.lower()
            mime = {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",
                    ".webp":"image/webp",".gif":"image/gif",".bmp":"image/bmp"}.get(ext, "image/jpeg")

    # 提示词 (跟 zhipu_ocr.py 同步)
    prompts = {
        "extract": (
            "请提取图片中所有文字内容, 数学公式用 LaTeX 格式 (例如 $\\frac{{a}}{{b}}$, $x^2$). "
            "保留题号 (如 1., (1), ①) 和分段. "
            "**直接输出提取的文本, 不要解释**. "
            "如果图片不清晰或不是文字内容, 输出 [无法识别]."
        ),
        "solve": (
            "请解答图片中的题目. 步骤:\n"
            "1. **提取题目**: 完整抄写题目的文字, 公式用 LaTeX.\n"
            "2. **分析**: 简短说明解题思路 (1-3 句).\n"
            "3. **解答**: 给出完整步骤 + 最终答案.\n"
            "如果有多个小题, 用 (1), (2), (3) 分别作答."
        ),
    }

    try:
        from zhipuai import ZhipuAI
        client = ZhipuAI(api_key=api_key)

        b64 = base64.b64encode(img_bytes).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"

        resp = client.chat.completions.create(
            model="glm-4v",  # 不用 flash: flash 在某些条件下返 code 1210
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompts[mode]},
                ],
            }],
            temperature=0.1,
            max_tokens=1024,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"(zhipu_ocr error: {type(e).__name__}: {e})"


def tool_multimodal_solve(image_path: str, qa_func) -> tuple[str, list, str]:
    """**多模态 RAG 解题** - OCR 提题面 → RAG 找文档 → LLM 结合两者解答.

    工作流:
    1. OCR (extract 模式) 拿题面文字
    2. 用题面文字当 query 调 RAG (qa_func), 拿文档片段
    3. 把 (题面 + 文档片段) 喂给 LLM, 让它结合两者综合解答
    4. 返回: (final_answer, sources, ocr_question)

    参数:
      image_path: 题图绝对路径
      qa_func: ultimate_rag.make_ultimate_qa() 的 qa 函数 (question -> (answer, sources))

    返回: (final_answer, sources, extracted_question_text)
    """
    # Step 1: OCR 提题面 (extract 模式, 不要 solve)
    raw = tool_zhipu_ocr(image_path, mode="extract")

    # 检查 OCR 是否成功
    if raw.startswith("(zhipu_ocr error"):
        return raw, [], ""

    # 如果题面太短, 直接 OCR solve, 跳过 RAG
    extracted = raw.strip()
    if len(extracted) < 10 or "[无法识别]" in extracted:
        # 回退到纯 OCR solve
        answer = tool_zhipu_ocr(image_path, mode="solve")
        return f"⚠️ OCR 识别题面不完整, 仅靠图片识别解答:\n\n{answer}", [], extracted

    # Step 2: RAG 用题面检索
    try:
        rag_answer, sources = qa_func(extracted)
    except Exception as e:
        rag_answer, sources = "", []
        print(f"[multimodal] RAG search failed: {e}")

    # Step 3: 把题面 + RAG 片段喂给 LLM 综合
    import os
    from langchain_openai import ChatOpenAI
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "(multimodal error: 缺 DEEPSEEK_API_KEY)", sources, extracted

    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0.1,
        base_url="https://api.deepseek.com/v1",
        api_key=api_key, timeout=120,
    )

    # 截断 RAG 答案, 避免 prompt 太大
    rag_snippet = (rag_answer or "")[:3000] if rag_answer else "（RAG 没找到相关文档）"

    synthesis_prompt = (
        "你是一名解题助手. 学生发了一道题 (从图片 OCR 提取) 和相关参考文档.\n"
        "请结合参考文档解答学生的问题. 如果参考文档不相关或答案不可靠, 用你自己的知识回答.\n\n"
        f"【题面】\n{extracted}\n\n"
        f"【参考文档】\n{rag_snippet}\n\n"
        "输出要求:\n"
        "- 直接给答案, 不要分步骤说'我已经分析了题面'这种\n"
        "- 如果参考文档有相关解答, 引用要点\n"
        "- 用 LaTeX 写公式 (例: $\\frac{a}{b}$)\n"
        "- (1)(2)(3) 分小题作答\n"
    )

    try:
        resp = llm.invoke(synthesis_prompt)
        final_answer = resp.content if hasattr(resp, 'content') else str(resp)
    except Exception as e:
        final_answer = f"(multimodal synthesis error: {type(e).__name__}: {e})"

    return final_answer, sources, extracted


# ======================== Agent ========================

SYSTEM_PROMPT = """你是 Web Agent (Phase 2 + OCR). 用 4 个工具回答问题:

工具优先级 (严格遵守):
1. **rag_search (优先)** - 本地 56 文档 (5 FTC + 1 飞机 + 50 智回社/FTC 笔记), 3-7 秒返回答案. FTC/机器人/比赛/智回社/路径规划相关问题**必须**先调它.
2. **zhipu_ocr (新增)** - 智谱 GLM-4V 多模态 OCR. 适合学生题目截图 (含公式用 LaTeX, 可顺便解题).
3. **search_web** - 本地答不了/查最新信息时用. cn.bing.com 国内直连.
4. **fetch_url** - 拿到 URL 后深入读正文.

收敛策略:
- **FTC / 机器人 / 比赛 / 计分 / 路径规划 / 视觉 / RAG / Pedro / 智回社** 相关 → 先调 rag_search (本地几乎都有答案)
- **题目截图 OCR / 解题** → zhipu_ocr (image_path 必传绝对路径)
- **最新新闻 / 论文 / 论文版本 / 软件下载 / 2026-2027 新版** → search_web
- **拿到 URL 但要详情** → fetch_url (但不要连续 fetch 多个 URL, 1 个就够了)
- **总计最多 4 次工具调用**, 超过就停止搜, 给出已知信息 + "需要查更多请换个关键词"

输出格式:
- 中文回答
- 关键事实带来源 ([1] [2] 编号, 对应工具返回结果)
- 如实说 "本地 + Web 都找不到" 而不要编造"""


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("[ERROR] 没设 DEEPSEEK_API_KEY")
        sys.exit(1)

    print("[INFO] 加载 Web Agent (LangChain v1.0) + 3 tools...")
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="deepseek-chat", temperature=0,
        base_url="https://api.deepseek.com/v1",
        api_key=api_key,
        timeout=120,
    )

    # rag_search 排第一 - 让 LLM 系统提示优先看
    tools = [tool_rag_search, tool_zhipu_ocr, tool_search_web, tool_fetch_url]
    react_agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        debug=False,
    )

    print(f"[INFO] Agent ready (tools: {[t.__name__ for t in tools]})")
    print(f"[INFO] recursion_limit=20 (防止无限搜索)")
    print()
    print("=" * 60)
    print("  Web Agent ready (Phase 2)")
    print("  本地 RAG (5FTC+1飞机) + cn.bing.com 搜索 + URL 抓取")
    print("  输入问题按回车, 输入 quit/exit 退出")
    print("=" * 60)
    print()

    while True:
        try:
            q = input("\nQ> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("quit", "exit"):
            break

        t0 = time.time()
        try:
            result = react_agent.invoke(
                {"messages": [("user", q)]},
                config={"recursion_limit": 20},
            )
            elapsed = time.time() - t0
            print(f"\n[A] (took {elapsed:.1f}s)")
            # 最后一条 assistant 消息
            for msg in reversed(result["messages"]):
                if msg.type == "ai":
                    print(msg.content)
                    break
        except Exception as e:
            print(f"[ERROR] {e}")
        print()


if __name__ == "__main__":
    main()