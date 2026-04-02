import hashlib
import logging
import time
import asyncio
from dataclasses import dataclass
from typing import Union, List, Dict, Optional, Any
from concurrent.futures import ProcessPoolExecutor

from anyio import to_thread
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.services.chunk_text import TextSplitter, SplitConfig
from app.services.pdf_viewer import PDFProcessor, PDFProcessorConfig
from app.services.utils.ocr_fallback import extract_text_with_ocr
from app.services.vector_store import VectorStore
import os

logger = logging.getLogger(__name__)

# ===============================
# Config
# ===============================

@dataclass
class ProcessorConfig:
    """
    Controls PDF ingestion behavior:
    - chunk_mode: which chunking strategy to use ("semantic" | "legal" | "fast")
    - min_chars_per_chunk: discard ultra-short chunks (noise)
    - dedupe: remove exact duplicate chunks by normalized content
    """
    chunk_mode: str = "semantic"
    min_chars_per_chunk: int = 50
    dedupe: bool = True


# ===============================
# Helpers
# ===============================

def _normalize_text(s: str) -> str:
    """Collapse whitespace for stable content hashing."""
    return " ".join((s or "").split()).strip()

# ===============================
# Main
# ===============================

class SmartDocumentProcessor:
    """
    PDF ingestor:
      - PDF extraction (with OCR fallback)
      - smart chunking via TextSplitter (legal / semantic / fast[=recursive])
      - filter out ultra-short chunks and optional dedupe
      - one-shot save into FAISS (VectorStore rebuilds per-document index)
    """

    def __init__(
        self,
        cfg: ProcessorConfig = ProcessorConfig(),
        split_cfg: SplitConfig = SplitConfig(),
    ):
        self.cfg = cfg
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
        self.embeddings = OpenAIEmbeddings(model=self.embedding_model)
        self.vector_store = VectorStore(
            embedding_model=self.embedding_model,
            embeddings=self.embeddings,
        )

        if cfg.chunk_mode == "legal":
            self.splitter = TextSplitter(
                legal_mode=True,
                semantic_mode=True,
                cfg=split_cfg,
                embeddings=self.embeddings,
            )
        elif cfg.chunk_mode == "semantic":
            self.splitter = TextSplitter(
                legal_mode=False,
                semantic_mode=True,
                cfg=split_cfg,
                embeddings=self.embeddings,
            )
        else: 
            self.splitter = TextSplitter(
                legal_mode=False,
                semantic_mode=False,
                cfg=split_cfg,
            )

        self.pdf_processor = PDFProcessor(
            cfg=PDFProcessorConfig(
                use_ocr_fallback=True,
                keep_full_page_text=True,
                skip_empty_pages=True,
                trim_whitespace=True,
                keep_spans=True,
            ),
            ocr_fn=extract_text_with_ocr,
        )

    # --------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------

    async def ingest(
        self,
        source: Union[str, bytes],
        doc_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ingest a PDF into FAISS.

        Args:
            source: PDF file path or bytes
            doc_id: stable document identifier
            filename (kwarg): optional filename metadata

        Returns:
            Dict[str, Any]: status + counters + timings
        """
        try:
            logger.info("PDF ingest start doc_id=%s source_type=%s", doc_id, type(source).__name__)

            if isinstance(source, (str, bytes)):
                return await self._ingest_pdf(source, doc_id, filename=kwargs.get("filename"))
            else:
                return {"status": "error", "doc_id": doc_id, "reason": "unsupported_source_type"}
        except Exception as e:
            logger.exception("PDF ingest failed doc_id=%s", doc_id)
            return {"status": "error", "doc_id": doc_id, "error": str(e)}

    # --------------------------------------------------------------
    # Internals
    # --------------------------------------------------------------

    async def _ingest_pdf(self, pdf_source: Union[str, bytes], doc_id: str, filename: Optional[str]) -> Dict[str, Any]:
        t0 = time.perf_counter()
        extracted = await to_thread.run_sync(self.pdf_processor.extract_pdf_pages, pdf_source, doc_id)
        t_extract = time.perf_counter() - t0

        if "error" in extracted:
            return {"status": "error", "doc_id": doc_id, "error": extracted["error"]}

        pages = extracted.get("pages", []) or []
        if not pages:
            return {"status": "error", "doc_id": doc_id, "reason": "no_pages_extracted"}

        split_docs: List[Document] = []
        try:
            has_spans = any(p.get("spans") for p in pages)
            if has_spans and hasattr(self.splitter, "split_pdf_pages_with_spans"):
                split_docs = self.splitter.split_pdf_pages_with_spans(pages, document_id=doc_id)
            else:
                for p in pages:
                    txt = p.get("content") or p.get("text") or ""
                    if not txt.strip():
                        continue
                    split_docs.extend(
                        self.splitter.split_text(text=txt, document_id=doc_id, page_number=p.get("pageNumber"))
                    )
        except Exception:
            logger.exception("Span-aware split failed; falling back to text-only.")

            split_docs = []
            for p in pages:
                txt = p.get("content") or p.get("text") or ""
                if not txt.strip():
                    continue
                split_docs.extend(
                    self.splitter.split_text(text=txt, document_id=doc_id, page_number=p.get("pageNumber"))
                )

        docs: List[Document] = []
        for d in split_docs:
            md = dict(d.metadata or {})
            if filename:
                md.setdefault("filename", filename)
            if "chunkId" not in md:
                preview = d.page_content[:50] if d.page_content else ""
                md["chunkId"] = f"fallback_{hash(preview) % 10000:04d}"
            docs.append(Document(page_content=d.page_content, metadata=md))

        docs = self._filter_min_len(docs, self.cfg.min_chars_per_chunk)
        docs_unique = self._dedupe(docs) if self.cfg.dedupe else docs
        if not docs_unique:
            return {"status": "error", "doc_id": doc_id, "reason": "no_usable_chunks_after_split"}

        t1 = time.perf_counter()
        await self._save_to_vector_store(docs_unique)
        t_store = time.perf_counter() - t1

        result = {
            "status": "success",
            "doc_id": doc_id,
            "pages_processed": len(pages),
            "ocr_used": extracted.get("metadata", {}).get("ocrUsed", False),
            "chunk_count": len(docs_unique),
            "stored": len(docs_unique),
            "timings": {
                "extract_s": round(t_extract, 3), 
                "store_s": round(t_store, 3)},
        }
        logger.info(
            "Ingest done doc_id=%s pages=%s chunks=%s stored=%s timings=%s",
            doc_id, len(pages), len(docs_unique), result["stored"], result["timings"]
        )
        return result

    # --------------------------------------------------------------
    # Utilities
    # --------------------------------------------------------------

    def _filter_min_len(self, docs: List[Document], min_chars: int) -> List[Document]:
        """Drop micro-chunks below a minimum character length."""
        if min_chars <= 0:
            return docs
        out: List[Document] = []
        for d in docs:
            content = (d.page_content or "").strip()
            if len(content) >= min_chars:
                out.append(d)
        return out

    def _dedupe(self, docs: List[Document]) -> List[Document]:
        """Remove exact duplicates by normalized page_content hash."""
        seen: set[str] = set()
        unique: List[Document] = []
        for d in docs:
            key = hashlib.sha256(_normalize_text(d.page_content).encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            unique.append(d)
        return unique

    async def _save_to_vector_store(self, docs: List[Document]) -> None:
        """Save documents using process pool for CPU-intensive FAISS work."""
        await asyncio.to_thread(self._save_with_retry, docs)

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, RuntimeError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    
    def _save_with_retry(self, docs: List[Document]) -> None:
        """
        Synchronous write of all chunks in one call.
        VectorStore will rebuild (delete + recreate) the per-document FAISS index.
        """
        self.vector_store.save_to_faiss(docs=docs)
        