# 从 v0.1.3 到 v0.1.6：4 次迭代构建一个生产级 RAG

> **作者**: ZCR327 · **仓库**: [ZCR327/llm-rag-lab](https://github.com/ZCR327/llm-rag-lab) · **日期**: 2026-09-22 · **技术栈**: Python · LangChain v1.4 · FAISS · 智谱 Embedding-2 · DeepSeek Chat · BGE-reranker-base

## 一句话总结

一周内从零搭了一个 RAG 系统，迭代 4 次，每次都给我上了一课。

| 版本 | 变化 | 学到的 |
|---|---|---|
| **v0.1.3** | 基础 RAG（chunk + embedding + top-3 + LLM）| 能跑，但 top-3 太窄 |
| **v0.1.4** | + query 改写 + top-10 + BGE rerank + top-3 | 答案更精炼，多 1-2 秒延迟 |
| **v0.1.5** | A/B 对比脚本 | 抓到了 v0.1.4 引入的幻觉（v0.1.3 没有）|
| **v0.1.6** | + "绝对不要编造" prompt 约束 | **一句话消除幻觉** |

最大的意外：**一行 prompt 文本**（`NEVER fabricate ...`）能消除一个**整个 advanced RAG 流水线引入的幻觉**。

---

## v0.1.3 —— 起点

最朴素的 RAG。教科书流水线：

```python
# 加载文档 → 切块 → embedding → FAISS top-3 → DeepSeek chat → 答案
docs = DirectoryLoader(data_dir, glob="**/*.md").load()
chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
index = FAISS.from_documents(chunks, ZhipuAIEmbeddings())
retriever = index.as_retriever(search_kwargs={"k": 3})
qa = RetrievalQA.from_chain_type(llm=ChatOpenAI(model="deepseek-chat"), retriever=retriever)
```

**优点**：简单（~120 行），快（每次查询 1-2 秒），demo 够用。

**缺点**：top-3 太窄。如果最好的块排在第 4 或第 5 名，LLM 永远看不到它。还有，短查询（比如"v5.5 极限多少分"）能匹配到"v5.5"但匹配不到"82 分"。

---

## v0.1.4 —— Advanced RAG：query 改写 + rerank

按 [Gao 2023 Advanced RAG 综述](https://arxiv.org/abs/2312.10997) 加了两个改进：

1. **Query rewriting**：让 DeepSeek 把用户问题改写成更精确的检索查询
2. **Cross-encoder rerank**：先用 bi-encoder 召回 top-10，再用 BGE-reranker-base 交叉编码器重排到 top-3

```python
rewritten = deepseek_llm.invoke(f"改写这个查询让检索更准: {q}")
candidates = index.similarity_search(rewritten, k=10)
scores = bge_reranker.predict([(rewritten, d.page_content) for d in candidates])
top3 = [d for s, d in sorted(zip(scores, candidates), reverse=True)[:3]]
answer = deepseek_llm.invoke(prompt.format(context=top3, question=q))
```

**代价**：每次查询多 1-2 秒（多 1 次 LLM 改写 + 本地 CPU rerank）。

**收益**：答案明显更精炼、更切题。reranker 有效过滤掉边缘相关块。

**踩坑**：BGE-reranker-base（~100MB 模型）要从 HuggingFace 下载。官方 `huggingface.co` 在国内访问不稳。修法是设环境变量 `HF_ENDPOINT=https://hf-mirror.com`。**一个环境变量，无代码改动**。

---

## v0.1.5 —— A/B 对比抓到了一个幻觉

我写了个并排对比脚本，5 个问题两个版本都跑一遍。结果**出乎意料**。

**问题**："8 POLLEN 累积一次的物理依据是什么？"

- **v0.1.3 答案**："资料未提供 8 POLLEN 累积一次的物理依据。这个 8/6 数值是用户确认的规则，不是从物理推导的。"
- **v0.1.4 答案**："物理依据是**球重力累计**——FLOWER CELL 装满 8 POLLEN 后，球的重力累计达到临界，HIVE pivot 翻倒触发 TIP。"

v0.1.4 的答案**自信、流畅、错误**。我的资料里**根本没提过重力**。advanced RAG 流水线反而让 LLM **更敢编**。

为什么？我写 v0.1.4 的 ANSWER_PROMPT 时写的是：

> "你是一个基于参考资料回答问题的助手. 如果资料不包含答案, 老实说不知道."

"如果资料不包含答案"这句话太软。LLM 把"8 POLLEN"+"物理依据"+"累计临界"组合成"看起来我能解释"——虽然资料里从未建立这个连接。rerank 后的 top-3 比 v0.1.3 召回的 top-3 **更短**（更"像答案"），但**信息量更低**。

v0.1.3 召回的某个块里写"这是用户确认的规则"——这个**元信息**本身在告诉 LLM "别外推"。v0.1.4 rerank 反而偏好"8 POLLEN 翻倒"一起出现的块——**看起来像可答的问题**。

---

## v0.1.6 —— 一行 prompt 修好

修复小得意外。我在 system prompt 加了两条约束：

```python
ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个基于参考资料回答问题的助手. "
               "**严格基于参考资料**回答. 如果资料里没有明确说某个事实, "
               "必须老实说'不知道'或'资料未提供', "
               "**绝对不要编造**未在资料中出现的物理原理、数字、原因、推导. "
               "回答简洁, 用中文."),
    ("human", "参考资料:\n{context}\n\n问题: {question}\n\n答案:"),
])
```

关键改动：
1. **"严格基于"** —— 更强的绑定
2. **"绝对不要编造"** —— 显式禁止
3. **"未在资料中出现的物理原理"** —— 点名幻觉的具体形式

改完后 v0.1.4 Q5 答案变成：

> "资料未提供 8 POLLEN 累积一次的物理依据。资料[1]和[2]只说明这是'跷跷板累积机制'且'用户确认'，但未给出任何物理原理或推导。"

召回的块一样。reranker 一样。LLM 一样。**只有 prompt 变了**。幻觉消失。

---

## 5 个核心经验

### 1. RAG 准确性是 prompt 工程问题

检索质量重要，但最终答案的真实性被"如果资料没说就承认"这条 LLM compliance 卡着。一句含糊的"基于资料回答"不够。**显式"NEVER fabricate"** 才能堵住漏洞。

### 2. Advanced RAG 可能**引入**幻觉（反直觉）

更复杂的检索可能产生更自信的错误答案。reranker 选中"看起来像答案"的块时，LLM 把这块当定论，感觉有资格外推。基础检索（top-3 更广）有时反而召回含"这是用户确认的规则"元信息的块——元信息本身在告诉 LLM "别外推"。

→ **建议**：在 held-out 测试集上测量**幻觉率**，不只是答案质量。

### 3. A/B 测试是必须的

没有并排跑两个版本读答案，我永远不会发现 v0.1.4 的幻觉。"更精炼"可能等于"更错"。

### 4. 网络本地化是 2026 年一等工程问题

四次迭代里有三次撞墙：OpenAI 平台 OAuth 回调、huggingface.co 模型下载、pypi.org pip 装包。修法都是同一个模式：换镜像（`hf-mirror.com`、`pypi.tuna.tsinghua.edu.cn`）或换国产 provider（DeepSeek 替 OpenAI、智谱替 OpenAI Embeddings）。`scripts/run_local.ps1` 现在**第一天**就配清华 pip 镜像。

### 5. LangChain v1.x 迁移基本是机械操作

v1.4 三个 breaking change（2026-9 当时）：
- `langchain.text_splitter` → `langchain_text_splitters`
- `langchain.chains` → `langchain_classic.chains`
- `langchain_community` 退役中 —— 慢慢迁到独立集成包

30 分钟 debug 全部修完。

---

## 接下来

这篇博客覆盖 RAG 项目的第 1-4 周。剩余 2026-2027 计划：

- **Week 8**：个人变体实验。设计 1 个检索或 prompt 改进，**在 held-out 测试集上跑 A/B**，写报告。这是未来 EPQ 论文的核心。
- **Phase 2（2027 Q1）**：在这个 RAG 上加 Web Agent 层，让 agent 能搜文档 + 浏览网页。
- **Phase 3（2027 Q3+）**：独立仓库 `ZCR327/rl-lab`，RL + 机器人控制，串 FTC 路径规划。

公开 GitHub 仓库 [ZCR327/llm-rag-lab](https://github.com/ZCR327/llm-rag-lab) 是这个项目的活笔记。Issue、PR、实验记录都进那里。

如果你们也在搭类似 RAG 系统，**今天最高杠杆的改动是给答案 prompt 加 "NEVER fabricate" 那一行**。免费、30 秒、消除一类错误——任何检索工程都修不掉。