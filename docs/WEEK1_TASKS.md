# Week 1 Tasks — 5h total (~3 sessions)

**Goal:** get the minimal RAG demo running end-to-end locally.

## Session 1 (~2h, Sat morning)

- [ ] `git init` + first commit (scaffold already on disk, you commit)
- [ ] Create GitHub repo `ZCR327/llm-rag-lab` (public, MIT license)
- [ ] `python -m venv .venv` + activate it
- [ ] `pip install -r requirements.txt`
- [ ] Get a DeepSeek API key at https://platform.deepseek.com/ (国内直连, 免费额度够 demo)
- [ ] Get a ZhipuAI API key at https://bigmodel.cn/ (国内直连, GLM Embedding-2 免费)
- [ ] `cp .env.example .env` + paste both keys

## Session 2 (~2h, Sun morning)

- [ ] Put 3-5 sample `.txt` files into `data/raw/`
  (Wikipedia articles, lecture notes, FTC game manual excerpt — any coherent text)
- [ ] `python src/minimal_rag.py` — index builds, no errors
- [ ] Ask 5 questions, eyeball the retrieved docs make sense
- [ ] If errors hit, debug:
  - `.env` not loaded → check `python-dotenv` install
  - OpenAI 401 → key wrong or billing not enabled
  - Index fails → check `data/raw/` has actual `.txt` files

## Session 3 (~1h, next Sat)

- [ ] `git add .` + first push to GitHub
- [ ] Update README with your GitHub link
- [ ] Screenshot working demo, save in `experiments/week1_demo.png`
- [ ] Commit: `feat: week 1 minimal RAG demo running`

## Stretch goals (only if time left)

- [ ] Try a different `CHUNK_SIZE` (200, 1000) — how does answer quality change?
- [ ] Try a different embedding model
- [ ] Add a Flask web UI instead of CLI loop (replace the `input()` loop)