import pytest
from app.services.chunk_text import AdvancedTextSplitter
from langchain_core.documents import Document

@pytest.fixture
def mock_encoder(mocker):
    mock = mocker.patch("app.services.chunk_text.tiktoken.get_encoding")
    encoder = mock.return_value
    encoder.encode.side_effect = lambda x: list(range(len(x)))
    return encoder

@pytest.fixture
def mock_embeddings(mocker):
    return mocker.patch("app.services.chunk_text.OpenAIEmbeddings")

def test_empty_text_returns_empty_list(mock_encoder, mock_embeddings):
    splitter = AdvancedTextSplitter(semantic_mode=True)
    result = splitter.split_text("", document_id="doc1")
    assert result == []

def test_legal_mode_splits_by_sections(mock_encoder, mock_embeddings):
    text = "§1 First section text.\n§2 Second section text."
    splitter = AdvancedTextSplitter(legal_mode=True, semantic_mode=False)
    result = splitter.split_text(text, document_id="doc2")

    assert len(result) == 2
    assert all(doc.metadata["chunkType"] == "legal" for doc in result)
    assert result[0].metadata["heading"] == "§1"
    assert result[1].metadata["heading"] == "§2"

def test_headings_split_correctly(mock_encoder, mock_embeddings, mocker):
    text = "## Intro\nIntro text\n\n## Details\nMore text"

    mocker.patch("app.services.chunk_text.AdvancedTextSplitter._remove_boilerplate", return_value=text)

    splitter = AdvancedTextSplitter(legal_mode=False, semantic_mode=False)
    result = splitter.split_text(text, document_id="doc3")

    assert len(result) >= 2
    assert result[0].metadata["chunkType"] == "hierarchical"
    assert result[0].metadata["heading"] == "Intro"

def test_generic_fallback_chunking(mock_encoder, mock_embeddings):
    text = "No headings or legal symbols. Just plain text. " * 20
    splitter = AdvancedTextSplitter(legal_mode=False, semantic_mode=False)
    result = splitter.split_text(text, document_id="doc4")

    assert len(result) >= 1
    assert all(doc.metadata["chunkType"] in ("generic", "recursive") for doc in result)

def test_semantic_chunking_fallbacks_to_recursive(mock_encoder, mocker):
    text = "This is a long sentence. " * 100
    mock_encoder.encode.side_effect = lambda x: list(range(len(x)))
    mocker.patch("app.services.chunk_text.OpenAIEmbeddings", return_value=mocker.Mock())
    mock_semantic_chunker = mocker.patch("app.services.chunk_text.SemanticChunker")
    mock_semantic_chunker_instance = mock_semantic_chunker.return_value
    mock_semantic_chunker_instance.create_documents.side_effect = Exception("fail")

    splitter = AdvancedTextSplitter(semantic_mode=True)
    result = splitter.split_text(text, document_id="doc5")

    assert len(result) > 0
    assert all(doc.metadata["chunkType"] == "recursive" for doc in result)
