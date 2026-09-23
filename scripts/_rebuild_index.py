# -*- coding: utf-8 -*-
"""重建 RAG 索引 - 添加 Pedro Pathing 后"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# v0.1.17: 用 dotenv (ultimate_rag 内部也 load_dotenv, 冗余但保险)
import os
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)

from ultimate_rag import build_or_load_index
print("[INFO] 开始重建索引...")
idx, n_docs, n_chunks = build_or_load_index()
print(f"[OK] 索引完成: {n_docs} 文档, {n_chunks} chunks")
print(f"[OK] 保存到 data/embeddings/")