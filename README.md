# llm-rag-lab

Personal RAG (Retrieval-Augmented Generation) research lab.

Self-directed exploration of the Lewis et al. 2020 RAG paper, advanced RAG
architectures, and personal variants. Built incrementally over 4-6 months
on ~5h/week. Phase 2 (Q1 2027) will add a Web Agent layer on top of this RAG.

## Status

- **Phase 1 (current, ~2026.9 → 2027.2):** reproduce + extend Lewis et al. 2020 RAG,
  build a minimal demo (FAISS + LangChain + Flask).
- **Phase 2 (planned, ~2027.3 → summer):** add a Web Agent layer using this RAG
  as a knowledge base.

See `docs/WEEK1_TASKS.md` for the weekly plan, `docs/PAPERS.md` for the
reading list.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # then edit .env with OPENAI_API_KEY
# put some .txt files in data/raw/
python src/minimal_rag.py
```

## Layout

```
llm-rag-lab/
├── src/                # Python source
├── data/               # raw documents + embeddings (gitignored)
├── experiments/        # experiment logs + results
├── docs/               # notes, paper reading notes, weekly plans
├── requirements.txt
├── .gitignore
├── .env.example
├── CHANGELOG.md
└── README.md
```

## Roadmap

- [x] Repo scaffold (v0.1.0)
- [ ] Week 1: minimal RAG demo running locally
- [ ] Week 4: advanced RAG (re-ranking, query rewriting)
- [ ] Week 8: first personal-variant experiment with writeup
- [ ] Week 16: technical blog post + arXiv submission draft
- [ ] Week 20: Phase 2 (Web Agent) kickoff

## License

MIT