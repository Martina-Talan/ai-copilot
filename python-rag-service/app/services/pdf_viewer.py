from __future__ import annotations
import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union
import fitz
from langchain_core.documents import Document
from app.services.chunk_text import AdvancedTextSplitter

logger = logging.getLogger(__name__)

SPACE_RE = re.compile(r"[ \t]+")
BLANKS_RE = re.compile(r"\n{3,}")
PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")  
BOILERPLATE_WORDS_RE = re.compile(r"\b(?:Confidential|Draft)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*([^\n#].*?)\s*$")


def _mk_id(*parts: object) -> str:
    """Stable short id for pages/chunks."""
    return hashlib.sha1("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()[:16]


@dataclass
class PDFProcessorConfig:
    """Config knobs to tune behavior without changing code."""
    use_ocr_fallback: bool = True
    max_pages: Optional[int] = None        
    keep_full_page_text: bool = True         
    skip_empty_pages: bool = True          
    trim_whitespace: bool = True             


class PDFProcessor:
    def __init__(
        self,
        splitter: Optional[AdvancedTextSplitter] = None,
        cfg: PDFProcessorConfig = PDFProcessorConfig(),
        ocr_fn: Optional[Callable[[fitz.Page], str]] = None,  
    ):
        """
        :param splitter: Inject your AdvancedTextSplitter (or it will create a default one).
        :param cfg: PDF processing config.
        :param ocr_fn: Optional OCR function to call if page has no extractable text.
        """
        self.cfg = cfg
        self.text_splitter = splitter or AdvancedTextSplitter(
            legal_mode=True,
            semantic_mode=True,
        )
        self.ocr_fn = ocr_fn 
        logger.info(
            "PDFProcessor initialized use_ocr=%s max_pages=%s",
            self.cfg.use_ocr_fallback,
            self.cfg.max_pages,
        )


    def extract_pdf_pages(
        self,
        source: Union[str, bytes],
        doc_id: str,
        password: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Extracts per-page text + RAG-ready chunks with rich metadata.

        Returns:
            {
              "metadata": {...},
              "pages": [ {page info ...}, ... ],
              "chunks": [ {"page_content": "...", "metadata": {...}}, ... ]
            }
        """
        try:
            open_kwargs = self._build_open_kwargs(source, password)
            pages_out: List[Dict] = []
            all_chunks_out: List[Dict] = []

            with fitz.open(**open_kwargs) as doc:
                total_pages = len(doc)
                page_limit = self.cfg.max_pages or total_pages
                logger.info("Processing PDF doc_id=%s pages=%s (limit=%s)", doc_id, total_pages, page_limit)

                for page_idx in range(min(total_pages, page_limit)):
                    page = doc.load_page(page_idx)
                    page_num = page_idx + 1

                    text, source_tag = self._extract_text_for_page(page)
                    if self.cfg.trim_whitespace:
                        text = self._clean_text(text)

                    if not text.strip() and self.cfg.skip_empty_pages:
                        logger.debug("Skipping empty page %s/%s (doc_id=%s)", page_num, total_pages, doc_id)
                        continue

                    headings = self._extract_headings(text)
                    page_id = _mk_id(doc_id, page_num)

                    if self.cfg.keep_full_page_text:
                        pages_out.append({
                            "pageNumber": page_num,
                            "pageId": page_id,
                            "textSource": source_tag,                
                            "headings": headings,                     
                            "wordCount": len(text.split()),
                            "charCount": len(text),
                            "pageIndicator": f"Page {page_num}/{total_pages}",
                            "content": text,
                        })
                    else:
                        pages_out.append({
                            "pageNumber": page_num,
                            "pageId": page_id,
                            "textSource": source_tag,
                            "headings": headings,
                            "wordCount": len(text.split()),
                            "charCount": len(text),
                            "pageIndicator": f"Page {page_num}/{total_pages}",
                        })

                    documents: List[Document] = self.text_splitter.split_text(
                        text=text,
                        document_id=doc_id,
                        page_number=page_num,
                    )
                    
                    for d in documents:
                        md = dict(d.metadata)
                        md.setdefault("chunkId", _mk_id(doc_id, page_num, md.get("heading"), md.get("chunkType"), d.page_content[:80]))
                        all_chunks_out.append({
                            "page_content": d.page_content,
                            "metadata": md,
                        })

            return {
                "metadata": {
                    "documentId": doc_id,
                    "totalPages": len(pages_out),
                    "maxPagesEvaluated": self.cfg.max_pages,
                    "ocrUsed": any(p.get("textSource") == "ocr" for p in pages_out),
                },
                "pages": pages_out,
                "chunks": all_chunks_out,
            }

        except Exception:
            logger.exception("PDF processing failed doc_id=%s", doc_id)
            return {
                "error": "PDF processing failed",
                "documentId": doc_id,
            }

    def _build_open_kwargs(self, source: Union[str, bytes], password: Optional[str]) -> Dict[str, object]:
        if isinstance(source, (bytes, bytearray)):
            kwargs: Dict[str, object] = {"stream": source, "filetype": "pdf"}
        elif isinstance(source, str):
            kwargs = {"filename": source}
        else:
            raise TypeError("source must be a file path (str) or PDF bytes.")
        if password:
            kwargs["password"] = password
        return kwargs

    def _extract_text_for_page(self, page: fitz.Page) -> Tuple[str, str]:
        """
        First try embedded text; if empty and OCR enabled + ocr_fn provided, use OCR.
        Returns (text, source_tag) where source_tag in {"text", "ocr"}.
        """
        text = (page.get_text("text") or "").strip()
        if text:
            return text, "text"

        if self.cfg.use_ocr_fallback and self.ocr_fn:
            try:
                ocr_text = (self.ocr_fn(page) or "").strip()
                if ocr_text:
                    return ocr_text, "ocr"
            except Exception:
                logger.exception("OCR fallback failed on page %s", page.number + 1)

        return "", "text"

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace and drop trivial boilerplate."""
        if not text:
            return ""

        text = BOILERPLATE_WORDS_RE.sub("", text)
        text = SPACE_RE.sub(" ", text)
        text = BLANKS_RE.sub("\n\n", text)
        lines = [ln for ln in (ln.strip() for ln in text.split("\n")) if ln and not PAGE_NUM_RE.match(ln)]
        return "\n".join(lines).strip()

    def _extract_headings(self, text: str) -> List[Dict[str, object]]:
        """Detect markdown-style headings (##, ###, …)."""
        out: List[Dict[str, object]] = []
        for line in text.split("\n"):
            m = HEADING_RE.match(line)
            if m:
                hashes = len(line) - len(line.lstrip("#"))
                out.append({
                    "text": m.group(1).strip(),
                    "level": hashes,
                })
        return out
