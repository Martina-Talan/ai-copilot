import pytest
from langchain_core.documents import Document

@pytest.fixture
def anyio_backend():
    return "asyncio"

# ---------- Fakes ----------

class FakeFAISSStore:
    """Minimal FAISS store carrying a .docstore attribute."""
    def __init__(self, docstore):
        self.docstore = docstore


class FakeDocStoreDict:
    """docstore with the ._dict branch"""
    def __init__(self, mapping):
        self._dict = dict(mapping)


class FakeDocStoreDocs:
    """docstore with the ._docs branch"""
    def __init__(self, mapping):
        self._docs = dict(mapping)


class FakeVectorStore:
    """
    Drop-in for VectorStore inside load_all_chunks.
    STORE is a class variable tests can set per-case.
    """
    STORE = None

    def __init__(self, *args, **kwargs):
        pass

    def safe_load_faiss_store(self, document_id, index_dir=None, as_retriever=False):
        return FakeVectorStore.STORE


# ---------- Fixture ----------

@pytest.fixture
def patch_loader(monkeypatch):
    import app.services.utils.load_all_chunks as mod
    monkeypatch.setattr(mod, "VectorStore", FakeVectorStore, raising=True)
    return mod


# ---------- Helper to quickly build Documents ----------

def _doc(text, doc_id, page=None, heading=None, chunk_id=None):
    md = {
        "documentId": doc_id,
        "pageNumber": page,
        "heading": heading,
        "chunkId": chunk_id,
    }
    return Document(page_content=text, metadata=md)


# ---------- Tests ----------

@pytest.mark.anyio
async def test_happy_path_dedupe_sort_limit_with__dict(patch_loader):
    """Filters by documentId, dedupes by chunkId, sorts, and respects max_items (. _dict branch)."""
    from app.services.utils.load_all_chunks import load_all_chunks, LoadChunksConfig

    # Docs:
    # - d2 and d3 share the same chunkId -> dedupe removes one
    # - dX belongs to another documentId -> filtered out
    d1 = _doc("two",  "DOC", page=2, heading="B", chunk_id="c2")
    d2 = _doc("one",  "DOC", page=1, heading="A", chunk_id="c1")
    d3 = _doc("dup",  "DOC", page=1, heading="A", chunk_id="c1")
    dX = _doc("nope", "OTHER", page=3, heading="Z", chunk_id="x")

    docstore = FakeDocStoreDict({"a": d1, "b": d2, "c": d3, "x": dX})
    FakeVectorStore.STORE = FakeFAISSStore(docstore)

    cfg = LoadChunksConfig(max_items=None, dedupe_by_chunk_id=True, strict=False)
    docs = await load_all_chunks("DOC", cfg=cfg)

    # expect d2 (page=1) then d1 (page=2); d3 deduped, dX filtered out
    assert len(docs) == 2
    assert docs[0].metadata.get("pageNumber") == 1
    assert docs[1].metadata.get("pageNumber") == 2
    assert {d.metadata.get("chunkId") for d in docs} == {"c1", "c2"}
    assert all(d.metadata.get("documentId") == "DOC" for d in docs)


@pytest.mark.anyio
async def test_max_items_cap(patch_loader):
    """max_items trims the result after sorting."""
    from app.services.utils.load_all_chunks import load_all_chunks, LoadChunksConfig

    d1 = _doc("p2", "DOC", page=2, heading="B", chunk_id="c2")
    d2 = _doc("p1", "DOC", page=1, heading="A", chunk_id="c1")
    d3 = _doc("p3", "DOC", page=3, heading="C", chunk_id="c3")
    docstore = FakeDocStoreDict({"a": d1, "b": d2, "c": d3})
    FakeVectorStore.STORE = FakeFAISSStore(docstore)

    cfg = LoadChunksConfig(max_items=1, dedupe_by_chunk_id=True, strict=False)
    docs = await load_all_chunks("DOC", cfg=cfg)

    # sorted by pageNumber -> first is page=1; then cap to 1 item
    assert len(docs) == 1
    assert docs[0].metadata.get("pageNumber") == 1


@pytest.mark.anyio
async def test_missing_index_non_strict_returns_empty(patch_loader):
    """When the store is missing and strict=False, return an empty list."""
    from app.services.utils.load_all_chunks import load_all_chunks, LoadChunksConfig

    FakeVectorStore.STORE = None 

    cfg = LoadChunksConfig(strict=False)
    docs = await load_all_chunks("DOC", cfg=cfg)
    assert docs == []


@pytest.mark.anyio
async def test_missing_index_strict_raises(patch_loader):
    """When the store is missing and strict=True, raise FileNotFoundError."""
    from app.services.utils.load_all_chunks import load_all_chunks, LoadChunksConfig

    FakeVectorStore.STORE = None

    cfg = LoadChunksConfig(strict=True)
    with pytest.raises(FileNotFoundError):
        await load_all_chunks("DOC", cfg=cfg)


@pytest.mark.anyio
async def test_docstore__docs_branch(patch_loader):
    """Same logic via the ._docs branch of the docstore."""
    from app.services.utils.load_all_chunks import load_all_chunks, LoadChunksConfig

    d1 = _doc("alpha", "DOC", page=2, heading="B", chunk_id="c2")
    d2 = _doc("beta",  "DOC", page=1, heading="A", chunk_id="c1")
    d3 = _doc("skip",  "OTHER", page=9, heading="Z", chunk_id="x")
    ds = FakeDocStoreDocs({"a": d1, "b": d2, "x": d3})
    FakeVectorStore.STORE = FakeFAISSStore(ds)

    cfg = LoadChunksConfig(dedupe_by_chunk_id=True)
    docs = await load_all_chunks("DOC", cfg=cfg)

    assert len(docs) == 2
    assert [d.metadata.get("pageNumber") for d in docs] == [1, 2]
