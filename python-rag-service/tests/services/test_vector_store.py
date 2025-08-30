import os
from typing import List
from pathlib import Path

import pytest
from langchain_core.documents import Document

# ---------- Fakes (no external dependencies) ----------

class FakeEmbeddings:
    def __init__(self, *a, **k): pass
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Not actually used by FakeFAISS, kept for interface compatibility
        return [[len(t)] for t in texts]
    def embed_query(self, text: str) -> List[float]:
        return [len(text)]

class _DocStore:
    def __init__(self):
        self._dict = {}

class FakeFAISS:
    """Minimal imitation of LangChain's FAISS store."""
    _REGISTRY = {}  # path(str) -> instance

    def __init__(self, docs: List[Document] = None):
        self.docstore = _DocStore()
        self._docs: List[Document] = []
        if docs:
            self.add_documents(docs)

    @classmethod
    def from_documents(cls, docs, embeddings, **kwargs):
        # Build a brand-new "index" from documents
        return cls(docs)

    @classmethod
    def load_local(cls, path, embeddings, allow_dangerous_deserialization=True, **kwargs):
        inst = cls._REGISTRY.get(path)
        if inst is None:
            raise FileNotFoundError(f"FakeFAISS: nothing stored at {path}")
        return inst

    def add_documents(self, docs: List[Document]):
        for d in docs:
            self._docs.append(d)
            key = f"k{len(self.docstore._dict) + 1}"
            self.docstore._dict[key] = d

    def save_local(self, path: str):
        # Remember instance and create stub files expected by the loader
        FakeFAISS._REGISTRY[path] = self
        os.makedirs(path, exist_ok=True)
        Path(path, "index.faiss").write_bytes(b"fake-index")
        Path(path, "index.pkl").write_bytes(b"fake-pkl")

    def as_retriever(self, search_kwargs=None):
        k = (search_kwargs or {}).get("k", 10)
        parent = self
        class _R:
            def __init__(self, p, k): self.p, self.k = p, k
            def get_relevant_documents(self, query):
                # Return first k docs (good enough for testing)
                return self.p._docs[: self.k]
        return _R(parent, k)

# ---------- Auto-patch FAISS and Embeddings in the module under test ----------

@pytest.fixture(autouse=True)
def _patch_module(monkeypatch):
    import app.services.vector_store as mod
    monkeypatch.setattr(mod, "FAISS", FakeFAISS)
    monkeypatch.setattr(mod, "OpenAIEmbeddings", FakeEmbeddings)
    yield

# ---------- Helper ----------

def make_docs(n: int, doc_id: str = "D1") -> List[Document]:
    docs = []
    for i in range(1, n + 1):
        docs.append(
            Document(
                page_content=f"text {i}",
                metadata={"documentId": doc_id, "chunkId": f"{doc_id}-{i}"}
            )
        )
    return docs

# ---------- Tests ----------

def test_save_creates_index_dir(tmp_path):
    from app.services.vector_store import VectorStore, VectorStoreConfig
    cfg = VectorStoreConfig(index_base=str(tmp_path / "faiss_root"))
    vs = VectorStore(embedding_model="test-emb", cfg=cfg)

    docs = make_docs(3, doc_id="A")
    vs.save_to_faiss(docs)

    # Directory: <index_base>/<model_sanitized>/doc_<id>
    target = tmp_path / "faiss_root" / "test-emb" / "doc_A"
    assert target.is_dir()
    assert (target / "index.faiss").exists()
    assert (target / "index.pkl").exists()

def test_load_as_store_and_as_retriever(tmp_path):
    from app.services.vector_store import VectorStore, VectorStoreConfig
    cfg = VectorStoreConfig(index_base=str(tmp_path / "faiss_root"))
    vs = VectorStore(embedding_model="test-emb", cfg=cfg)

    vs.save_to_faiss(make_docs(5, "B"))

    # Raw store
    store = vs.load_faiss_store("B", as_retriever=False)
    assert hasattr(store, "docstore")
    assert len(store.docstore._dict) == 5

    # Retriever
    retr = vs.load_faiss_store("B", as_retriever=True, k=2)
    hits = retr.get_relevant_documents("anything")
    assert len(hits) == 2
    assert all(isinstance(h, Document) for h in hits)

def test_safe_load_returns_none_when_missing(tmp_path):
    from app.services.vector_store import VectorStore, VectorStoreConfig
    cfg = VectorStoreConfig(index_base=str(tmp_path / "faiss_root"))
    vs = VectorStore(embedding_model="test-emb", cfg=cfg)

    got = vs.safe_load_faiss_store("NOPE")
    assert got is None 

def test_similarity_search_returns_documents(tmp_path):
    from app.services.vector_store import VectorStore, VectorStoreConfig
    cfg = VectorStoreConfig(index_base=str(tmp_path / "faiss_root"))
    vs = VectorStore(embedding_model="test-emb", cfg=cfg)

    vs.save_to_faiss(make_docs(4, "C"))

    res = vs.similarity_search("C", "query", k=3)
    assert len(res) == 3
    assert all(isinstance(d, Document) for d in res)
