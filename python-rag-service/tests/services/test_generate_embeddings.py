import pytest
from langchain_core.documents import Document
from unittest.mock import Mock, AsyncMock
import asyncio
from concurrent.futures import ThreadPoolExecutor

# ---------- Fakes to isolate the unit ----------

class FakeVectorStore:
    """Captures what would be written to FAISS, without touching disk."""
    def __init__(self, *args, **kwargs):
        self.save_calls = 0
        self.last_saved_docs = None

    def save_to_faiss(self, docs):
        self.save_calls += 1
        self.last_saved_docs = list(docs)


class FakePDFProcessor:
    """Simulates PDF extraction."""
    def __init__(self):
        self.extract_calls = []
        
    def extract_pdf_pages(self, source, doc_id):
        self.extract_calls.append((source, doc_id))
        
        return {
            "metadata": {
                "documentId": doc_id,
                "totalPages": 2,
                "pagesReturned": 2,
                "ocrUsed": False
            },
            "pages": [
                {
                    "pageNumber": 1,
                    "content": "First page content with some text to chunk.",
                    "text": "First page content with some text to chunk.",
                    "spans": []
                },
                {
                    "pageNumber": 2, 
                    "content": "Second page with more content for testing.",
                    "text": "Second page with more content for testing.",
                    "spans": []
                }
            ],
            "chunks": []
        }


class FakeTextSplitter:
    """Simulates text splitting behavior."""
    def __init__(self):
        self.split_calls = []
        self.split_pages_calls = []
        
    def split_text(self, text, document_id, page_number=None):
        self.split_calls.append((text, document_id, page_number))
        
        return [
            Document(
                page_content="This is a sufficiently long chunk that passes the minimum length requirement for testing purposes.",
                metadata={"chunkId": f"{document_id}_chunk1", "pageNumber": page_number}
            )
        ]
    
    def split_pdf_pages_with_spans(self, pages, document_id):
        self.split_pages_calls.append((pages, document_id))
        chunks = []
        for page in pages:
            chunks.extend(self.split_text(
                page.get("content", ""), document_id, page.get("pageNumber")
            ))
        return chunks


# ---------- Fixtures ----------

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def fake_vector_store():
    return FakeVectorStore()

@pytest.fixture
def fake_pdf_processor():
    return FakePDFProcessor()

@pytest.fixture
def fake_text_splitter():
    return FakeTextSplitter()

@pytest.fixture
def processor_fast(fake_vector_store, fake_pdf_processor, fake_text_splitter, monkeypatch):
    """Processor with fast chunking mode."""
    from app.services.generate_embeddings import SmartDocumentProcessor, ProcessorConfig
    
    monkeypatch.setattr("app.services.generate_embeddings.VectorStore", lambda *args, **kwargs: fake_vector_store)
    monkeypatch.setattr("app.services.generate_embeddings.PDFProcessor", lambda *args, **kwargs: fake_pdf_processor)
    
    processor = SmartDocumentProcessor(cfg=ProcessorConfig(chunk_mode="fast"))
    processor.splitter = fake_text_splitter
    
    original_save = processor._save_to_vector_store
    
    async def mock_save(docs):
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, processor._save_with_retry, docs)
    
    processor._save_to_vector_store = mock_save
    
    return processor

# ---------- Tests ----------

@pytest.mark.anyio
async def test_ingest_pdf_success(processor_fast, fake_vector_store, fake_pdf_processor, fake_text_splitter):
    """Test successful PDF ingestion with fast chunking."""
    res = await processor_fast.ingest(b"%PDF-FAKE%", doc_id="DOC-P1", filename="test.pdf")
   
    print(f"RESULT: {res}")
    
    assert res["status"] == "success"
    assert res["doc_id"] == "DOC-P1"
    assert res["pages_processed"] == 2
    assert res["chunk_count"] > 0
    assert res["stored"] == res["chunk_count"]
    
    assert len(fake_pdf_processor.extract_calls) == 1
    assert fake_pdf_processor.extract_calls[0][1] == "DOC-P1"
    
    assert len(fake_text_splitter.split_calls) > 0
    
    assert fake_vector_store.save_calls == 1
    assert fake_vector_store.last_saved_docs is not None
    assert len(fake_vector_store.last_saved_docs) == res["stored"]

    for doc in fake_vector_store.last_saved_docs:
        assert "chunkId" in doc.metadata
        assert doc.metadata.get("filename") == "test.pdf"

@pytest.mark.anyio
async def test_ingest_pdf_deduplication(processor_fast, fake_vector_store, fake_pdf_processor):
    """Test that duplicate chunks are removed."""
    class DuplicateSplitter:
        def split_text(self, text, document_id, page_number=None):
            return [
                Document(
                    page_content="This is duplicate content that is long enough to pass the minimum length filter for testing.",
                    metadata={"chunkId": "dup1", "pageNumber": page_number}
                ),
                Document(
                    page_content="This is duplicate content that is long enough to pass the minimum length filter for testing.",
                    metadata={"chunkId": "dup2", "pageNumber": page_number}
                ),
                Document(
                    page_content="This is unique content that should be kept after deduplication process completes.",
                    metadata={"chunkId": "unique1", "pageNumber": page_number}
                )
            ]
    
    processor_fast.splitter = DuplicateSplitter()
    processor_fast.cfg.dedupe = True
    
    res = await processor_fast.ingest(b"%PDF%", doc_id="DOC-DEDUPE")
    
    print(f"DEDUPE RESULT: {res}")
    
    assert res["status"] == "success"
    assert res["stored"] == 2
    assert fake_vector_store.last_saved_docs is not None
    assert len(fake_vector_store.last_saved_docs) == 2

@pytest.mark.anyio
async def test_ingest_pdf_min_length_filter(processor_fast, fake_vector_store, fake_pdf_processor):
    """Test that short chunks are filtered out."""
    class ShortChunkSplitter:
        def split_text(self, text, document_id, page_number=None):
            return [
                Document(
                    page_content="Short",
                    metadata={"chunkId": "short1", "pageNumber": page_number}
                ),
                Document(
                    page_content="This is a longer chunk that should be kept because it meets the minimum length requirement.",
                    metadata={"chunkId": "long1", "pageNumber": page_number}
                )
            ]
    
    processor_fast.splitter = ShortChunkSplitter()
    processor_fast.cfg.min_chars_per_chunk = 10
    
    res = await processor_fast.ingest(b"%PDF%", doc_id="DOC-FILTER")
    
    assert res["status"] == "success"
    assert res["stored"] == 1
    assert fake_vector_store.last_saved_docs[0].page_content == "This is a longer chunk that should be kept because it meets the minimum length requirement."

@pytest.mark.anyio
async def test_ingest_pdf_error_handling(processor_fast, fake_pdf_processor):
    """Test error handling when PDF extraction fails."""
    original_extract = fake_pdf_processor.extract_pdf_pages
    
    def failing_extract(source, doc_id):
        return {"error": "PDF extraction failed", "documentId": doc_id}
    
    fake_pdf_processor.extract_pdf_pages = failing_extract
    
    try:
        res = await processor_fast.ingest(b"%PDF-CORRUPT%", doc_id="DOC-ERROR")
        
        assert res["status"] == "error"
        assert "PDF extraction failed" in res["error"]
        assert res["doc_id"] == "DOC-ERROR"
    finally:
        fake_pdf_processor.extract_pdf_pages = original_extract