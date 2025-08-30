import pytest
from app.services.pdf_viewer import PDFProcessor, PDFProcessorConfig


# ---------- Fake PDF ----------

class FakePage:
    def __init__(self, text=""):
        self._text = text
        self.number = 0

    def get_text(self, kind="text"):
        return self._text


class FakeDoc:
    """Minimal context manager simulating fitz.open result."""
    def __init__(self, pages_text):
        self._pages = [FakePage(t) for t in pages_text]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __len__(self):
        return len(self._pages)

    def load_page(self, i: int):
        return self._pages[i]


# ---------- Fixture ----------

@pytest.fixture
def cfg_default():
    return PDFProcessorConfig(
        use_ocr_fallback=True,
        keep_full_page_text=True,
        skip_empty_pages=True,
        trim_whitespace=True,
    )


# ---------- Tests ----------

def test_embedded_text_path(monkeypatch, cfg_default):
    """
    If PDF has embedded text, OCR is not called
    and 'text' is returned as the source.
    """
    def fake_open(**kwargs):
        return FakeDoc(["Hello world"])
    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    def ocr_fn_should_not_be_called(page):
        raise AssertionError("OCR should not be called for embedded text")

    proc = PDFProcessor(cfg=cfg_default, ocr_fn=ocr_fn_should_not_be_called)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc1")

    assert "error" not in out
    assert out["metadata"]["documentId"] == "doc1"
    assert out["pages"][0]["textSource"] == "text"
    assert out["pages"][0]["content"] == "Hello world"


def test_skip_empty_pages(monkeypatch):
    """
    If the page is empty and skip_empty_pages=True, it is skipped.
    """
    def fake_open(**kwargs):
        return FakeDoc(["   \n\n   "])
    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    cfg = PDFProcessorConfig(
        use_ocr_fallback=False,
        keep_full_page_text=True,
        skip_empty_pages=True,
        trim_whitespace=True,
    )
    proc = PDFProcessor(cfg=cfg, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-empty")

    assert "error" not in out
    assert out["pages"] == []


def test_trim_and_cleaning(monkeypatch, cfg_default):
    """
    Cleansing removes whitespace, 'Confidential', and page numbers.
    """
    raw = "  Confidential  \n\n  123  \n Actual  text \n\n"
    def fake_open(**kwargs):
        return FakeDoc([raw])
    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    proc = PDFProcessor(cfg=cfg_default, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-clean")

    assert "error" not in out
    txt = out["pages"][0]["content"]
    assert txt == "Actual text"


def test_error_payload_on_unexpected_failure(monkeypatch, cfg_default):
    """
    If fitz.open raises an error, a clear error payload is returned (no crash).
    """
    def fake_open(**kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    proc = PDFProcessor(cfg=cfg_default, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-fail")

    assert out["error"] == "PDF processing failed"
    assert out["documentId"] == "doc-fail"
