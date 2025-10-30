import pytest
from app.services.chunk_text import TextSplitter, SplitConfig

# ---------- Fixtures ----------

@pytest.fixture
def splitter():
    cfg = SplitConfig(
        rec_chunk_size=500,
        rec_overlap=50, 
    )
    return TextSplitter(cfg=cfg, semantic_mode=False) 

@pytest.fixture
def splitter_legal():
    return TextSplitter(cfg=SplitConfig(), semantic_mode=False, legal_mode=True)

@pytest.fixture
def mock_spans():
    return [
        {"text": "First line of text", "bbox": {"x": 10, "y": 10, "width": 50, "height": 10}},
        {"text": "Second line continues", "bbox": {"x": 10, "y": 25, "width": 60, "height": 10}},
    ]

@pytest.fixture
def splitter_with_small_chunks():
    """Splitter with smaller limits for testing."""
    cfg = SplitConfig(
        rec_chunk_size=500,
        rec_overlap=50,
        min_chars_per_chunk=10,
        max_tokens_single=100,
    )
    return TextSplitter(cfg=cfg, semantic_mode=False)

# ---------- Tests ----------

def test_generic_chunking_short_text(splitter):
    """Test basic chunking with short text that doesn't need splitting."""
    content = "This is a short paragraph that doesn't need splitting."
    chunks = splitter.split_text(content, document_id="doc-1")

    assert len(chunks) == 1
    assert chunks[0].metadata["chunkType"] == "generic"
    assert "short paragraph" in chunks[0].page_content
    assert chunks[0].metadata["documentId"] == "doc-1"

def test_heading_chunking(splitter):
    """Test chunking with markdown-style headings."""
    content = "# Title\nThis is section one.\n\n## Subtitle\nThis is section two."
    chunks = splitter.split_text(content, document_id="doc-2")

    assert len(chunks) == 2
    assert chunks[0].metadata["heading"] == "Title"
    assert chunks[0].metadata["chunkType"] == "hierarchical"
    assert "section one" in chunks[0].page_content

def test_legal_chunking(splitter_legal):
    """Test legal document chunking with section markers."""
    content = "§1 This is section one.\n\n§2 This is section two."
    chunks = splitter_legal.split_text(content, document_id="doc-3")

    assert len(chunks) == 2
    assert chunks[0].metadata["heading"] == "§1"
    assert chunks[0].metadata["chunkType"] == "legal"
    assert "section one" in chunks[0].page_content

def test_recursive_chunking_long_text(splitter):
    """Test that long text gets split into multiple chunks."""
    cfg = SplitConfig(
        rec_chunk_size=200,
        rec_overlap=20,
        max_tokens_single=100,
    )
    splitter = TextSplitter(cfg=cfg, semantic_mode=False)

    long_text = "This sentence. " * 100
    chunks = splitter.split_text(long_text, document_id="doc-4")

    assert len(chunks) > 1
    assert all("This sentence" in c.page_content for c in chunks)

def test_empty_text_returns_empty_list(splitter):
    """Empty input should return empty list."""
    chunks = splitter.split_text("", document_id="doc-empty")
    assert chunks == []

def test_whitespace_only_returns_empty_list(splitter):
    """Whitespace-only text should return empty list."""
    chunks = splitter.split_text("   \n\n   ", document_id="doc-whitespace")
    assert chunks == []

def test_token_counting_in_metadata(splitter):
    """Test that token counts are included in metadata."""
    content = "This is a test sentence for token counting."
    chunks = splitter.split_text(content, document_id="doc-tokens")
    
    assert len(chunks) == 1
    assert "tokenCount" in chunks[0].metadata
    assert isinstance(chunks[0].metadata["tokenCount"], int)
    assert chunks[0].metadata["tokenCount"] > 0

def test_split_pdf_pages_combined(splitter):
    """Test combining multiple PDF pages into chunks."""
    mock_pages = [
        {"text": "Page one content", "pageNumber": 1},
        {"text": "Page two content", "pageNumber": 2},
    ]
    
    chunks = splitter.split_pdf_pages_combined(mock_pages, "doc-pdf")
    
    assert len(chunks) > 0
    assert any("Page one" in chunk.page_content for chunk in chunks)
    assert any("Page two" in chunk.page_content for chunk in chunks)

def test_split_pdf_pages_with_spans(splitter_with_small_chunks, mock_spans):
    """Test chunking PDF pages with span information."""
    mock_pages = [
        {
            "pageNumber": 1,
            "spans": mock_spans,
            "text": "Fallback text"
        }
    ]
    
    chunks = splitter_with_small_chunks.split_pdf_pages_with_spans(mock_pages, "doc-spans-pdf")
    
    assert len(chunks) > 0
    assert chunks[0].metadata["chunkType"] == "by_spans"
    assert any("line" in chunk.page_content for chunk in chunks)  

def test_split_pdf_pages_fallback_to_text(splitter):
    """Test PDF pages without spans fallback to text chunking."""
    mock_pages = [
        {
            "pageNumber": 1,
            "text": "Page content without spans",
            "spans": []  
        }
    ]
    
    chunks = splitter.split_pdf_pages_with_spans(mock_pages, "doc-fallback")
    
    assert len(chunks) > 0
    assert "Page content" in chunks[0].page_content



