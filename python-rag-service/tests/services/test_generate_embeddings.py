import pytest
from langchain_core.documents import Document

@pytest.fixture
def anyio_backend():
    return "asyncio"

# ---------- Fakes to isolate the unit ----------

class FakeVectorStore:
    """
    Captures what would be written to FAISS, without touching disk.
    """
    def __init__(self, *args, **kwargs):
        self.save_calls = 0
        self.last_saved_docs = None

    def save_to_faiss(self, docs, index_dir=None):
        self.save_calls += 1
        # Keep a copy so tests can assert on it
        self.last_saved_docs = list(docs)


class FakePDFProcessor:
    """
    Simulates PDF extraction. Configure via class attributes in tests:
      - RETURN: dict returned by extract_pdf_pages
      - RAISE:  exception to throw
    """
    RETURN = {"metadata": {"documentId": "D"}, "pages": [], "chunks": []}
    RAISE = None

    def __init__(self, *args, **kwargs):
        pass

    def extract_pdf_pages(self, source, doc_id):
        if FakePDFProcessor.RAISE is not None:
            raise FakePDFProcessor.RAISE
        return FakePDFProcessor.RETURN


class FakeOpenAIEmbeddings:
    """
    Stub to avoid any real API calls when TextSplitter is constructed.
    """
    def __init__(self, *args, **kwargs):
        pass

# ---------- Monkeypatch generate_embeddings module ----------

@pytest.fixture
def patch_generate_embeddings(monkeypatch):
    import app.services.generate_embeddings as mod
    monkeypatch.setattr(mod, "VectorStore", FakeVectorStore, raising=True)
    monkeypatch.setattr(mod, "PDFProcessor", FakePDFProcessor, raising=True)
    monkeypatch.setattr(mod, "OpenAIEmbeddings", FakeOpenAIEmbeddings, raising=True)
    return {
        "module": mod,
        "FakeVectorStore": FakeVectorStore,
        "FakePDFProcessor": FakePDFProcessor,
        "FakeOpenAIEmbeddings": FakeOpenAIEmbeddings,
    }


# ----------  Processor fixtures ----------


@pytest.fixture
def processor_fast(patch_generate_embeddings):
    from app.services.generate_embeddings import SmartDocumentProcessor, ProcessorConfig
    # Fast mode -> RecursiveCharacterTextSplitter path (no embeddings)
    return SmartDocumentProcessor(cfg=ProcessorConfig(chunk_mode="fast"))


@pytest.fixture
def processor_semantic(patch_generate_embeddings):
    from app.services.generate_embeddings import SmartDocumentProcessor, ProcessorConfig
    # Semantic mode -> uses TextSplitter path (we’ll override it in one test)
    return SmartDocumentProcessor(cfg=ProcessorConfig(chunk_mode="semantic"))


# ----------  Tests ----------


@pytest.mark.anyio
async def test_ingest_texts_dedupe_and_minlen(processor_fast):
    """
    - Two texts normalize to the same content => deduped to 1
    - A micro-chunk below min_chars is dropped
    - VectorStore called exactly once with the final doc list
    """
    texts = [
        "Alpha   beta",   # normal text
        "Alpha beta",     # duplicate after whitespace normalization
        "x",              # too short -> filtered by min_chars_per_chunk=5 (default)
        "   ",            # empty -> skipped
    ]

    res = await processor_fast.ingest(texts, doc_id="DOC-T1")

    assert res["status"] == "success"
    assert res["stored"] == 1
    # Access the fake store on the instance
    saved = processor_fast.vector_store.last_saved_docs
    assert saved is not None
    assert len(saved) == 1
    # Ensure we really stored the deduped content
    assert "Alpha beta" in saved[0].page_content.replace("  ", " ")


@pytest.mark.anyio
async def test_ingest_pdf_success(processor_fast, patch_generate_embeddings):
    """
    Fake PDF returns two short pages; fast splitter yields one chunk per page.
    We expect 2 chunks stored in a single VectorStore call.
    """
    FakePDF = patch_generate_embeddings["FakePDFProcessor"]
    FakePDF.RAISE = None
    FakePDF.RETURN = {
        "metadata": {"documentId": "DOC-P1", "ocrUsed": False},
        "pages": [
            {"pageNumber": 1, "content": "First page text."},
            {"pageNumber": 2, "content": "Second page text."},
        ],
        "chunks": [],
    }

    res = await processor_fast.ingest(b"%PDF-FAKE%", doc_id="DOC-P1", filename="file.pdf")

    assert res["status"] == "success"
    assert res["stored"] == 2
    saved = processor_fast.vector_store.last_saved_docs
    assert saved is not None and len(saved) == 2
    # Each doc should carry a chunkId (fast branch assigns a fallback)
    assert all(d.metadata.get("chunkId") for d in saved)


@pytest.mark.anyio
async def test_ingest_pdf_error_bubbles_to_status(processor_fast, patch_generate_embeddings):
    """
    If the PDF processor raises, ingest should return status=error and include the message.
    """
    FakePDF = patch_generate_embeddings["FakePDFProcessor"]
    FakePDF.RAISE = RuntimeError("boom!")
    try:
        res = await processor_fast.ingest(b"%PDF-FAKE%", doc_id="DOC-P2")
    finally:
        FakePDF.RAISE = None  # cleanup for safety

    assert res["status"] == "error"
    assert "boom" in res.get("error", "").lower()


@pytest.mark.anyio
async def test_splitter_must_provide_chunk_id(processor_semantic, patch_generate_embeddings):
    """
    Guard-rail: When using TextSplitter path, if returned Documents lack 'chunkId',
    the processor should fail cleanly with a clear error.
    """
    # A splitter that IS a TextSplitter (subclass), but forgets to set chunkId
    from app.services.chunk_text import TextSplitter

    class BadSplitter(TextSplitter):
        def __init__(self):  # no super(), we don't need embeddings here
            pass
        def split_text(self, text, document_id, page_number=None):
            return [Document(page_content="No id here", metadata={"documentId": document_id})]

    # Replace splitter on the semantic processor so isinstance(..., TextSplitter) is True
    processor_semantic.splitter = BadSplitter()

    # Make PDF path execute (single page with content)
    FakePDF = patch_generate_embeddings["FakePDFProcessor"]
    FakePDF.RAISE = None
    FakePDF.RETURN = {
        "metadata": {"documentId": "DOC-NOID"},
        "pages": [{"pageNumber": 1, "content": "Some content"}],
        "chunks": [],
    }

    res = await processor_semantic.ingest(b"%PDF%", doc_id="DOC-NOID")
    assert res["status"] == "error"
    assert "splitter did not assign chunkid" in res.get("error", "").lower()
