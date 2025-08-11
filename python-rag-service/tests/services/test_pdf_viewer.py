import pytest
from langchain_core.documents import Document
from app.services.pdf_viewer import PDFProcessor

def test_extract_pdf_pages_with_mocked_fitz_and_splitter(mocker):
    mock_open = mocker.patch("app.services.pdf_viewer.fitz.open")
    mock_ctx = mocker.MagicMock()
    mock_doc = mocker.MagicMock()
    mock_ctx.__enter__.return_value = mock_doc
    mock_ctx.__exit__.return_value = False
    mock_open.return_value = mock_ctx

    mock_doc.__len__.return_value = 2
    mock_page1 = mocker.MagicMock()
    mock_page1.get_text.return_value = "## Heading 1\nSome text on page 1"
    mock_page2 = mocker.MagicMock()
    mock_page2.get_text.return_value = "## Heading 2\nSome text on page 2"
    mock_doc.load_page.side_effect = [mock_page1, mock_page2]

    split_mock_cls = mocker.patch("app.services.pdf_viewer.AdvancedTextSplitter")
    split_inst = split_mock_cls.return_value
    split_inst.split_text.side_effect = lambda text, document_id, page_number: [
        Document(
            page_content=f"chunk from page {page_number}",
            metadata={"documentId": document_id, "pageNumber": page_number, "chunkType": "generic"},
        )
    ]

    processor = PDFProcessor()
    result = processor.extract_pdf_pages(source="dummy.pdf", doc_id="doc123")

    assert result["metadata"]["documentId"] == "doc123"
    assert result["metadata"]["totalPages"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["headings"][0]["text"] == "Heading 1"
    assert result["pages"][1]["headings"][0]["text"] == "Heading 2"
    assert len(result["chunks"]) == 2
    assert result["chunks"][0]["metadata"]["pageNumber"] == 1
    assert result["chunks"][1]["metadata"]["pageNumber"] == 2
