import pytest
from app.services.chunk_text import TextSplitter, SplitConfig

# ---------- Fixture ----------

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


# ---------- Tests ----------

def test_generic_chunking_short_text(splitter):
    content = "This is a short paragraph that doesn't need splitting."
    chunks = splitter.split_text(content, document_id="doc-1")

    assert len(chunks) == 1
    assert chunks[0].metadata["chunkType"] == "generic"
    assert "short paragraph" in chunks[0].page_content

def test_heading_chunking(splitter):
    content = "# Title\nThis is section one.\n\n## Subtitle\nThis is section two."
    chunks = splitter.split_text(content, document_id="doc-2")

    assert len(chunks) == 2
    assert chunks[0].metadata["heading"] == "Title"
    assert chunks[0].metadata["chunkType"] == "hierarchical"
    assert "section one" in chunks[0].page_content

def test_legal_chunking(splitter_legal):
    content = "§1 This is section one.\n\n§2 This is section two."
    chunks = splitter_legal.split_text(content, document_id="doc-3")

    assert len(chunks) == 2
    assert chunks[0].metadata["heading"] == "§1"
    assert chunks[0].metadata["chunkType"] == "legal"
    assert "section one" in chunks[0].page_content

def test_boilerplate_cleanup(splitter):
    content = "   Confidential   \n\n\n123\n\nReal content.\n\n"
    cleaned = splitter._remove_boilerplate(content)

    assert "Confidential" not in cleaned
    assert "123" not in cleaned
    assert "Real content." in cleaned

def test_recursive_chunking_used_if_no_embeddings():
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

def test_id_line_preserved_after_cleanup(splitter):
    raw = "Calculation ID:\n902310\nThe client confirms..."
    cleaned = splitter._remove_boilerplate(raw)
    assert "902310" in cleaned
    assert "Calculation ID" in cleaned