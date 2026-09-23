# -*- coding: utf-8 -*-
"""重建 RAG 索引 - 添加 Pedro Pathing 后"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os
# 加载 .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

from ultimate_rag import build_or_load_index
print("[INFO] 开始重建索引...")
idx, n_docs, n_chunks = build_or_load_index()
print(f"[OK] 索引完成: {n_docs} 文档, {n_chunks} chunks")
print(f"[OK] 保存到 data/embeddings/")