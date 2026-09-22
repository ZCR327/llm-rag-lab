# From v0.1.3 to v0.1.6: Building a Production-Quality RAG in 4 Iterations

> **Author**: ZCR327 · **Repo**: [ZCR327/llm-rag-lab](https://github.com/ZCR327/llm-rag-lab) · **Date**: 2026-09-22 · **Stack**: Python · LangChain v1.4 · FAISS · ZhipuAI Embedding-2 · DeepSeek Chat · BGE-reranker-base

## TL;DR

In one week I built a RAG system from scratch and iterated it 4 times. Each version taught a different lesson. Here is the full journey and what I learned.

| Version | What changed | Lesson |
|---|---|---|
| **v0.1.3** | Basic RAG (chunk + embed + top-3 + LLM) | Baseline works, but top-3 is too narrow |
| **v0.1.4** | + Query rewrite + top-10 + BGE rerank + top-3 | Cleaner answers, +1-2s latency |
| **v0.1.5** | A/B comparison script | Caught a hallucination in v0.1.4 that v0.1.3 didn't have |
| **v0.1.6** | + "no fabrication" prompt constraint | One sentence fixed the hallucination |

The biggest surprise: a single line of prompt text (`NEVER fabricate ...`) eliminated a hallucination that an entire advanced RAG pipeline had introduced.

---

## v0.1.3 — The Baseline

I started with the simplest possible RAG. The pipeline is textbook:

```python
# load docs → chunk → embed → FAISS top-3 → DeepSeek chat → answer
docs = DirectoryLoader(data_dir, glob="**/*.md").load()
chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
index = FAISS.from_documents(chunks, ZhipuAIEmbeddings())
retriever = index.as_retriever(search_kwargs={"k": 3})
qa = RetrievalQA.from_chain_type(llm=ChatOpenAI(model="deepseek-chat"), retriever=retriever)
```

**Pros**: simple (~120 lines), fast (~1-2s per query), correct enough for a demo.

**Cons**: top-3 retrieval is too narrow. If the best chunk ranks 4th or 5th, the LLM never sees it. Also, vague queries like "v5.5 极限多少分" (what's the max score for v5.5?) get matched to "v5.5" mentions but not directly to the "82 分" fact.

---

## v0.1.4 — Advanced RAG: Query Rewriting + Reranking

I followed the [Gao et al. 2023 Advanced RAG survey](https://arxiv.org/abs/2312.10997) and added two improvements:

1. **Query rewriting**: ask DeepSeek to rewrite the user query into a more precise form before searching.
2. **Cross-encoder reranking**: retrieve top-10 candidates with bi-encoder, then rerank with BGE-reranker-base to select top-3.

```python
rewritten_query = deepseek_llm.invoke(f"Rewrite this query for better search: {q}")
candidates = index.similarity_search(rewritten_query, k=10)
reranked = bge_reranker.predict([(rewritten_query, d.page_content) for d in candidates])
top3 = [d for score, d in sorted(zip(reranked, candidates), reverse=True)[:3]]
answer = deepseek_llm.invoke(answer_prompt.format(context=top3, question=q))
```

**Cost**: +1-2 seconds per query (one extra LLM call for rewrite, local CPU inference for reranker).

**Win**: answers are noticeably more concise and on-topic. The reranker effectively filters out tangentially related chunks.

**Snag**: BGE-reranker-base (~100MB model) needs to be downloaded from HuggingFace. The official `huggingface.co` domain is unreliable from mainland China. The fix was setting `HF_ENDPOINT=https://hf-mirror.com`. One environment variable, no code change.

---

## v0.1.5 — A/B Comparison Caught a Hallucination

I wrote a side-by-side comparison script that runs both versions on 5 questions. The results were not what I expected.

**Question**: "8 POLLEN 累积一次的物理依据是什么?" (What's the physical basis for the 8-POLLEN accumulation?)

- **v0.1.3 answer**: "The source documents do not provide a physical basis for the 8-POLLEN accumulation. The 8/6 values are user-confirmed from the design document, not derived from physics."
- **v0.1.4 answer**: "The physical basis is **ball gravity accumulation** — once 8 POLLEN fill the FLOWER CELL, the cumulative gravity crosses a threshold, causing the HIVE pivot to tip."

The v0.1.4 answer is **confident, fluent, and wrong**. My source documents say nothing about gravity. The advanced RAG pipeline somehow made the LLM **more willing to hallucinate**, not less.

Why? When I wrote the ANSWER_PROMPT for v0.1.4, I used:

> "你是一个基于参考资料回答问题的助手. 如果资料不包含答案, 老实说不知道."

The English equivalent is roughly: "If the source material does not contain the answer, honestly say you don't know." The problem is the phrase "does not contain the answer" is too soft. The LLM interpreted "8 POLLEN" + "physical basis" + "cumulative threshold" as something it could plausibly explain, even though the source documents never made that connection. The rewrite + rerank pipeline produced a *shorter* context (reranker chose the 3 most "answer-like" chunks), but those chunks were actually **less informative** than the broader top-3 from v0.1.3.

The v0.1.3 pipeline retrieved a chunk that said "this is a user-confirmed rule" — which directly signaled "no physics here". The v0.1.4 reranker preferred a chunk that mentioned "8 POLLEN" and "翻倒" together — which *looked* like an answerable question.

---

## v0.1.6 — One Line of Prompt Fixed It

The fix was deceptively simple. I added two constraints to the system prompt:

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

The English version: "STRICTLY base your answer on the source. If a fact is not explicitly stated, you MUST say 'I don't know' or 'not in the source material'. **NEVER fabricate** physical principles, numbers, or reasoning not present in the sources."

The key changes:
1. **"严格基于"** / "STRICTLY based on" — stronger binding
2. **"绝对不要编造"** / "NEVER fabricate" — explicit prohibition
3. **"未在资料中出现的物理原理"** / "physical principles not in sources" — names the specific failure mode

After this change, v0.1.4's Q5 answer became:

> "资料未提供 8 POLLEN 累积一次的物理依据. 资料[1]和[2]只说明这是'跷跷板累积机制'且'用户确认', 但未给出任何物理原理或推导."

Same retrieved chunks. Same reranker. Same LLM. Same retrieval. **Only the prompt changed.** Hallucination gone.

---

## Takeaways

### 1. RAG accuracy is a prompt engineering problem

Retrieval quality matters, but the final answer's truthfulness is gated by the LLM's compliance with "if not in source, say so". A vague prompt like "answer based on context" is insufficient. The explicit "NEVER fabricate" instruction is what closes the loophole.

### 2. Advanced RAG can *introduce* hallucinations

Counter-intuitive: more sophisticated retrieval can produce more confident wrong answers. When the reranker picks a "looks-like-an-answer" chunk, the LLM treats that chunk as definitive and feels licensed to extrapolate. Basic retrieval (top-3 broader) sometimes returns chunks with the meta-information "this is a user-confirmed rule" which itself signals "don't extrapolate".

This suggests: **measure hallucination rate on a held-out set, not just answer quality**.

### 3. A/B testing is non-negotiable

I would not have caught the v0.1.4 hallucination without running both versions on the same questions and reading the answers side by side. "Cleaner" answers can be wrong answers.

### 4. Network locality is a first-class engineering concern in 2026

Three of the four iterations hit a wall because of mainland-China network issues: `platform.openai.com` auth callback, `huggingface.co` model download, and `pypi.org` pip install. The fixes were always the same pattern: use a mirror (`hf-mirror.com`, `pypi.tuna.tsinghua.edu.cn`) or switch to a CN-native provider (`DeepSeek` instead of OpenAI, `ZhipuAI` instead of OpenAI Embeddings). This is now part of the project's first-day setup (`scripts/run_local.ps1` configures the Tsinghua pip mirror automatically).

### 5. LangChain v1.x migration is mostly mechanical

Three breaking changes in v1.4 (as of Sep 2026):
- `langchain.text_splitter` → `langchain_text_splitters`
- `langchain.chains` → `langchain_classic.chains`
- `langchain_community` is being sunset — migrate to standalone integration packages over time

All caught and fixed within a 30-minute debugging session.

---

## What's Next

This blog covers weeks 1-4 of the project's RAG phase. The remaining 2026-2027 plan:

- **Week 8**: a personal RAG variant experiment. Design a retrieval or prompt improvement, run A/B against v0.1.6 on a held-out question set, write up the results. This is the centerpiece of any future EPQ thesis on this project.
- **Phase 2 (Q1 2027)**: layer a Web Agent on top of this RAG so the agent can search documents *and* browse the web.
- **Phase 3 (Q3 2027+)**: spin up a separate `ZCR327/rl-lab` repo for an RL + robotics-control project that ties into FTC path planning.

The public GitHub repository ([ZCR327/llm-rag-lab](https://github.com/ZCR327/llm-rag-lab)) is the live notebook for this work. Issues, PRs, and experiment logs all land there.

If you're working on a similar RAG system, the single highest-leverage change you can make today is to add the "NEVER fabricate" line to your answer prompt. It's free, takes 30 seconds, and eliminates a class of errors that no amount of retrieval engineering will fix.