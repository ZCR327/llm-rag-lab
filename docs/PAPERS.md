# Paper Reading List

## Primary target

**Lewis et al. 2020 — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"**
- arXiv: [2005.11401](https://arxiv.org/abs/2005.11401)
- Why: classic RAG paper, clean baseline, the one everyone references
- Read in order: §3 (RAG-Sequence, RAG-Token), §4 (experiments), §5 (results)
- Reproduce target: minimal end-to-end RAG pipeline (already in `src/minimal_rag.py`)
- Personal variant target: try a different retriever / different chunking / different fusion

## Secondary (after Week 4)

**Gao et al. 2023 — "Retrieval-Augmented Generation for Large Language Models: A Survey"**
- arXiv: [2312.10997](https://arxiv.org/abs/2312.10997)
- Why: comprehensive survey + Advanced RAG architectures (re-ranking, HyDE, query rewriting)
- Reproduce target: add at least 2 Advanced RAG features to the minimal demo

## Optional deep dives (later, when curious)

- **Borgeaud et al. 2022** — "Improving Language Models by Retrieving from Trillions of Tokens" (RETRO)
- **Izacard et al. 2022** — "Atlas: Few-shot Learning with Retrieval Augmented Language Models"
- **Karpukhin et al. 2020** — "Dense Passage Retrieval for Open-Domain Question Answering" (DPR — the retriever backbone)

## Phase 2 — Web Agent (~2027.3)

- **Yao et al. 2023** — "ReAct: Synergizing Reasoning and Acting in Language Models"
- **Significant Gravitas 2023** — "AutoGPT" (architecture reference)
- **OpenAI 2024** — "Operator" system card (when public)

## Reading rhythm

- Week 1-2: skim Lewis 2020 + read the LangChain docs
- Week 4-6: read Gao 2023 survey + pick 1-2 Advanced RAG techniques
- Week 8+: read targeted papers for the personal-variant experiment