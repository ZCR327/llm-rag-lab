# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-09-20

### Changed
- Provider swap: OpenAI (CN-blocked) -> DeepSeek chat + ZhipuAI embedding (both 国内直连)
- `src/minimal_rag.py`: use DeepSeek `deepseek-chat` via OpenAI-compat base_url, ZhipuAI `embedding-2`
- `.env.example`: dual key (`DEEPSEEK_API_KEY` + `ZHIPU_API_KEY`)
- `requirements.txt`: add `zhipuai>=2.0.0`
- `docs/WEEK1_TASKS.md`: updated setup steps for new providers

## [0.1.0] - 2026-09-20

### Added
- Repo scaffold: README, .gitignore, .env.example, requirements.txt
- `src/minimal_rag.py`: minimal end-to-end RAG demo (FAISS + LangChain + OpenAI)
- `docs/WEEK1_TASKS.md`: 5h/week task breakdown for Week 1
- `docs/PAPERS.md`: paper reading list (Lewis et al. 2020 primary, Gao 2023 secondary)