# -*- coding: utf-8 -*-
"""
agent.py — Web Agent (Phase 2) 加在 RAG 仓库

基于 v0.1.14 ultimate_rag (multi-query + BGE rerank + hyde-conservative)
加 3 个 tool:
- rag_search: **优先调用**, 覆盖本地 5 FTC + 1 飞机文档
- search_web: cn.bing.com HTML 爬 (主, 直连, 免 key) + Brave API (opt) + DDG (last fallback)
- fetch_url: 抓取 + 提取正文 (httpx + BS4)

使用 LangGraph v1.0 新 API: from langchain.agents import create_agent
- system_prompt 引导工具优先级 + 收敛策略
- recursion_limit=20 防止无限循环

Usage:
    # 装包: pip install -U langchain langgraph beautifulsoup4 httpx (清华源)
    # 设环境变量: $env:DEEPSEEK_API_KEY = "sk-..."
    # (可选) 设 $env:BRAVE_API_KEY = "BSA..." 切换 Brave Search API (国外)
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
        reranker = make_reranker()
        qa = make_ultimate_qa(index, multi_chain, hyde_chain, reranker, llm)
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


# ======================== Agent ========================

SYSTEM_PROMPT = """你是 Web Agent (Phase 2). 用 3 个工具回答问题:

工具优先级 (严格遵守):
1. **rag_search (优先)** - 本地 6 文档 (5 FTC + 1 飞机), 4-6 秒返回答案. FTC/机器人/比赛相关问题**必须**先调它.
2. **search_web** - 本地答不了/查最新信息时用. cn.bing.com 国内直连.
3. **fetch_url** - 拿到 URL 后深入读正文.

收敛策略:
- **FTC / 机器人 / 比赛 / 计分 / 路径规划 / 视觉 / RAG / Pedro** 相关 → 先调 rag_search (本地几乎都有答案)
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
    tools = [tool_rag_search, tool_search_web, tool_fetch_url]
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