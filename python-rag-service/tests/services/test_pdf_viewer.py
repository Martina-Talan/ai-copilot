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

class FakeRect:
    def __init__(self, height: float):
        self.height = height

class FakePageWithSpans(FakePage):
    def __init__(self, text="", rawdict=None, height=1000.0):
        super().__init__(text=text)
        self._rawdict = rawdict or {}
        self.rect = FakeRect(height)

    def get_text(self, kind="text"):
        if kind == "rawdict":
            return self._rawdict
        return super().get_text(kind=kind)

class FakeDocWithSpans(FakeDoc):
    def __init__(self, pages: list):
        self._pages = pages


# ---------- Helpers to build a minimal rawdict line ----------

def make_line(text: str, bbox=(10.0, 100.0, 110.0, 130.0)):
    return {
        "bbox": bbox,
        "spans": [{"text": text}],
    }

def make_rawdict(lines):
    return {
        "blocks": [
            {"lines": lines}
        ]
    }

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


def test_spans_extraction_basic(monkeypatch, cfg_default):
    """
    Extracts line-level spans with bbox and text; returns bottom-left coordinates.
    """
    raw = make_rawdict([make_line("Hello spans", (10.0, 100.0, 110.0, 130.0))])
    page = FakePageWithSpans(text="Hello spans", rawdict=raw, height=1000.0)

    def fake_open(**kwargs):
        return FakeDocWithSpans([page])

    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    proc = PDFProcessor(cfg=cfg_default, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-spans-basic")

    assert "error" not in out
    spans = out["pages"][0]["spans"]
    assert len(spans) == 1
    s = spans[0]
    assert s["text"] == "Hello spans"
    assert s["bbox"]["x"] == 10.0
    assert s["bbox"]["width"] == 100.0 
    assert s["bbox"]["height"] == 30.0  
    assert s["bbox"]["y"] == 870.0      


def test_spans_coordinate_conversion_bottom_left(monkeypatch, cfg_default):
    """
    Verifies Y conversion from PyMuPDF top-left to PDF bottom-left space for multiple lines.
    """
    lines = [
        make_line("L1", (0.0, 150.0, 50.0, 200.0)),
        make_line("L2", (5.0, 470.0, 55.0, 480.0)),
    ]
    raw = make_rawdict(lines)
    page = FakePageWithSpans(text="L1\nL2", rawdict=raw, height=500.0)

    def fake_open(**kwargs):
        return FakeDocWithSpans([page])

    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    proc = PDFProcessor(cfg=cfg_default, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-spans-coords")

    spans = out["pages"][0]["spans"]
    by_text = {s["text"]: s["bbox"]["y"] for s in spans}
    assert by_text["L1"] == 500.0 - 200.0 
    assert by_text["L2"] == 500.0 - 480.0  


def test_spans_skips_empty_and_invalid(monkeypatch, cfg_default):
    """
    Skips lines with empty text and non-positive geometry.
    """
    valid   = make_line("OK", (10.0, 10.0, 60.0, 30.0))
    empty   = make_line("   ", (0.0, 0.0, 100.0, 10.0))    
    flat    = make_line("flat", (10.0, 10.0, 10.0, 20.0)) 
    neg     = make_line("neg", (20.0, 20.0, 10.0, 10.0))   

    raw = make_rawdict([empty, flat, neg, valid])
    page = FakePageWithSpans(text="OK", rawdict=raw, height=200.0)

    def fake_open(**kwargs):
        return FakeDocWithSpans([page])

    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    proc = PDFProcessor(cfg=cfg_default, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-spans-skip")

    spans = out["pages"][0]["spans"]
    assert len(spans) == 1
    assert spans[0]["text"] == "OK"


def test_spans_flag_disabled(monkeypatch):
    """
    When keep_spans=False, spans field is not present in page records.
    """
    raw = make_rawdict([make_line("X", (0.0, 0.0, 10.0, 10.0))])
    page = FakePageWithSpans(text="X", rawdict=raw, height=100.0)

    def fake_open(**kwargs):
        return FakeDocWithSpans([page])

    monkeypatch.setattr("app.services.pdf_viewer.fitz.open", fake_open)

    cfg = PDFProcessorConfig(
        use_ocr_fallback=False,
        keep_full_page_text=True,
        skip_empty_pages=True,
        trim_whitespace=True,
        keep_spans=False,
    )
    proc = PDFProcessor(cfg=cfg, ocr_fn=None)
    out = proc.extract_pdf_pages(source=b"%PDF-FAKE%", doc_id="doc-spans-off")

    assert "error" not in out
    assert "spans" not in out["pages"][0]

