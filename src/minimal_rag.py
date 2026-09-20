"""
minimal_rag.py — minimal end-to-end RAG demo (Lewis et al. 2020 style)

Pipeline: load docs → chunk → embed (OpenAI text-embedding-3-small) →
FAISS index → retrieve top-k → generate (GPT-4o-mini) → answer with sources.

Setup:
    1. cp .env.example .env  (set OPENAI_API_KEY)
    2. Put some .txt files in data/raw/
    3. python src/minimal_rag.py

Target: ~120 lines, no fancy config, easy to read end-to-end.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# --- config ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise SystemExit(
        "OPENAI_API_KEY not set. Copy .env.example to .env and paste your key."
    )

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "embeddings"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3


def load_docs():
    if not DATA_DIR.exists() or not any(DATA_DIR.iterdir()):
        raise SystemExit(
            f"No documents found in {DATA_DIR}. "
            f"Drop some .txt files there first."
        )
    loader = DirectoryLoader(
        str(DATA_DIR), glob="**/*.txt", loader_cls=TextLoader
    )
    return loader.load()


def build_index(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
    index = FAISS.from_documents(chunks, embeddings)
    index.save_local(str(INDEX_DIR))
    return index, len(chunks)


def load_index():
    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
    return FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )


def make_qa(index):
    retriever = index.as_retriever(search_kwargs={"k": TOP_K})
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
    )


def main():
    # 1. Build or load index
    if (INDEX_DIR / "index.faiss").exists():
        print("[INFO] Loading existing FAISS index...")
        index = load_index()
    else:
        print("[INFO] Building new FAISS index from documents...")
        docs = load_docs()
        index, n_chunks = build_index(docs)
        n_docs = len(list(DATA_DIR.iterdir()))
        print(f"[OK] Indexed {n_docs} doc files into {n_chunks} chunks.")

    # 2. Build QA chain
    qa = make_qa(index)

    # 3. Interactive Q&A loop
    print("[INFO] Ready. Type 'quit' to exit.\n")
    while True:
        try:
            q = input("Q> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("quit", "exit"):
            break
        result = qa.invoke({"query": q})
        print(f"\nA> {result['result']}")
        for i, doc in enumerate(result["source_documents"], 1):
            src = doc.metadata.get("source", "?")
            print(f"  [{i}] {src}")


if __name__ == "__main__":
    main()