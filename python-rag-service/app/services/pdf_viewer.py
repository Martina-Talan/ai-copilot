from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid5, NAMESPACE_URL

import fitz

logger = logging.getLogger(__name__)

# ==============================================================
# Regex Utilities
# ==============================================================

SPACE_RE = re.compile(r"[ \t]+")
BLANKS_RE = re.compile(r"\n{3,}")
PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")
BOILERPLATE_WORDS_RE = re.compile(r"\b(?:Confidential|Draft)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*([^\n#].*?)\s*$")


def _page_id(doc_id: str, page_number: int) -> str:
    """Deterministic short id for a page (UUIDv5 shortened to 16 hex)."""
    return uuid5(NAMESPACE_URL, f"{doc_id}:{page_number}").hex[:16]


# ==============================================================
# Config
# ==============================================================

@dataclass
class PDFProcessorConfig:
    """Controls PDF extraction behavior."""
    use_ocr_fallback: bool = True
    max_pages: Optional[int] = None
    keep_full_page_text: bool = True
    skip_empty_pages: bool = True
    trim_whitespace: bool = True


# ==============================================================
# PDF Processor
# ==============================================================

class PDFProcessor:
    """
    Extract per-page text from a PDF (no chunking here).

    Flow:
      1) Try embedded text.
      2) If empty and OCR is enabled and `ocr_fn` is provided, run OCR (no caching).
      3) Normalize text if configured; skip empty pages if configured.

    Returns a dict:
      {
        "metadata": {documentId, totalPages, pagesReturned, maxPagesEvaluated, ocrUsed},
        "pages": [ {pageNumber, pageId, textSource, headings, wordCount, charCount, content?}, ... ],
        "chunks": []
      }

    On failure:
      {"error": "PDF processing failed", "documentId": <doc_id>}
    """

    def __init__(
        self,
        cfg: PDFProcessorConfig = PDFProcessorConfig(),
        ocr_fn: Optional[Callable[[fitz.Page], str]] = None,
    ):
        """
        Initialize PDF processor.

        Args:
            cfg (PDFProcessorConfig): Configuration options for PDF extraction, such as OCR usage,
                                  whitespace trimming, and page limits.
            ocr_fn (Callable, optional): Optional OCR function to extract text from image-based pages.

        """
        self.cfg = cfg
        self.ocr_fn = ocr_fn
        logger.info("PDFProcessor init use_ocr=%s max_pages=%s", cfg.use_ocr_fallback, cfg.max_pages)

    # --------------------------------------------------------------
    # Main extraction method
    # --------------------------------------------------------------

    def extract_pdf_pages(
        self,
        source: Union[str, bytes],
        doc_id: str,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read pages, optionally run OCR, and return page records."""
        try:
            open_kwargs = self._open_kwargs(source, password)
            pages_out: List[Dict[str, Any]] = []

            with fitz.open(**open_kwargs) as doc:
                total = len(doc)
                limit = min(self.cfg.max_pages or total, total)
                if limit < 0:
                    limit = 0

                logger.info("Processing PDF doc_id=%s pages=%s (limit=%s)", doc_id, total, limit)

                for i in range(limit):  
                    page = doc.load_page(i)
                    page_num = i + 1

                    text, src = self._page_text(page)
                    if self.cfg.trim_whitespace:
                        text = self._clean(text)

                    if not text.strip() and self.cfg.skip_empty_pages:
                        logger.debug("Skipping empty page %s/%s doc_id=%s", page_num, total, doc_id)
                        continue

                    record: Dict[str, Any] = {
                        "pageNumber": page_num,
                        "pageId": _page_id(doc_id, page_num),
                        "textSource": src, 
                        "headings": self._headings(text),
                        "wordCount": len(text.split()),
                        "charCount": len(text),
                        "pageIndicator": f"Page {page_num}/{total}",
                    }
                    if self.cfg.keep_full_page_text:
                        record["content"] = text
                    pages_out.append(record)

            return {
                "metadata": {
                    "documentId": doc_id,
                    "totalPages": total,
                    "pagesReturned": len(pages_out),
                    "maxPagesEvaluated": self.cfg.max_pages,
                    "ocrUsed": any(p.get("textSource") == "ocr" for p in pages_out),
                },
                "pages": pages_out,
                "chunks": [],  # chunking happens elsewhere
            }

        except Exception:
            logger.exception("PDF processing failed doc_id=%s", doc_id)
            return {"error": "PDF processing failed", "documentId": doc_id}

    # ==============================================================
    # Internals
    # ==============================================================
    def _open_kwargs(self, source: Union[str, bytes], password: Optional[str]) -> Dict[str, Any]:
        """Build arguments for fitz.open()."""
        if isinstance(source, (bytes, bytearray)):
            kw: Dict[str, Any] = {"stream": source, "filetype": "pdf"}
        elif isinstance(source, str):
            kw = {"filename": source}
        else:
            raise TypeError("source must be a file path (str) or PDF bytes.")
        if password:
            kw["password"] = password
        return kw

    def _page_text(self, page: fitz.Page) -> Tuple[str, str]:
        """
        Return (text, source_tag) using embedded text first, then OCR (no cache).
        source_tag ∈ {"text", "ocr"}.
        """
        txt = (page.get_text("text") or "").strip()
        if txt:
            return txt, "text"

        if self.cfg.use_ocr_fallback and self.ocr_fn:
            try:
                ocr_txt = (self.ocr_fn(page) or "").strip()
                if ocr_txt:
                    return ocr_txt, "ocr"
            except Exception:
                logger.warning("OCR failed on page %s", getattr(page, "number", "?"), exc_info=True)

        return "", "text"

    def _clean(self, text: str) -> str:
        """Normalize whitespace and trim trivial boilerplate."""
        if not text:
            return ""
        text = re.sub(r'\b(?:Confidential|Draft)\b', '', text, flags=re.IGNORECASE)
        text = SPACE_RE.sub(" ", text)
        text = BLANKS_RE.sub("\n\n", text)
        lines = [ln.strip() for ln in text.split("\n")]
        lines = [ln for ln in lines if ln and not ln.strip().isdigit()]
        return "\n".join(lines).strip()

    def _headings(self, text: str) -> List[Dict[str, Any]]:
        """Detect markdown-style headings (##, ###, …)."""
        out: List[Dict[str, Any]] = []
        for line in text.split("\n"):
            m = HEADING_RE.match(line)
            if not m:
                continue
            hashes = len(line) - len(line.lstrip("#"))
            out.append({"text": m.group(1).strip(), "level": hashes})
        return out
