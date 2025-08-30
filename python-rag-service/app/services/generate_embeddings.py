import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Union, List, Dict, Optional, Any

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
    Controls ingestion behavior:
    - chunk_mode: which chunking strategy to use ("semantic" | "legal" | "fast")
    - min_chars_per_chunk: discard ultra-short chunks (noise)
    - dedupe: remove exact duplicate chunks by normalized content
    """
    chunk_mode: str = "semantic"
    min_chars_per_chunk: int = 5
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
    PDF/text ingestor:
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
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
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
        else:  # "fast" -> recursive fallback via TextSplitter (semantic_mode=False)
            self.splitter = TextSplitter(
                legal_mode=False,
                semantic_mode=False,
                cfg=split_cfg,
            )

        self.pdf = PDFProcessor(
            cfg=PDFProcessorConfig(
                use_ocr_fallback=True,
                keep_full_page_text=True,
                skip_empty_pages=True,
                trim_whitespace=True,
            ),
            ocr_fn=extract_text_with_ocr,
        )

    # --------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------

    async def ingest(
        self,
        source: Union[str, bytes, List[str]],
        doc_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ingest a source into FAISS.

        Args:
            source: str/bytes -> PDF path/bytes; list[str] -> pre-supplied texts
            doc_id: stable document identifier
            filename (kwarg): optional filename metadata
            metadata (kwarg): optional base metadata for text ingestion

        Returns:
            Dict[str, Any]: status + counters + timings (or {"status":"error", ...})
        """
        try:
            logger.info("Ingest start doc_id=%s source_type=%s", doc_id, type(source).__name__)
            if isinstance(source, (str, bytes, bytearray)):
                return await self._ingest_pdf(source, doc_id, filename=kwargs.get("filename"))
            elif isinstance(source, list):
                return await self._ingest_texts(source, doc_id, base_metadata=kwargs.get("metadata"))
            else:
                return {"status": "error", "doc_id": doc_id, "reason": "unsupported_source_type"}
        except Exception as e:
            logger.exception("Ingest failed doc_id=%s", doc_id)
            return {"status": "error", "doc_id": doc_id, "error": str(e)}

    # --------------------------------------------------------------
    # Internals
    # --------------------------------------------------------------

    async def _ingest_pdf(self, pdf_source: Union[str, bytes], doc_id: str, filename: Optional[str]) -> Dict[str, Any]:
        """Extract pages from PDF, chunk them, and write a fresh FAISS index."""
        t0 = time.perf_counter()
        extracted = await to_thread.run_sync(self.pdf.extract_pdf_pages, pdf_source, doc_id)
        t_extract = time.perf_counter() - t0

        if "error" in extracted:
            return {"status": "error", "doc_id": doc_id, "error": extracted["error"]}

        pages = extracted.get("pages", []) or []
        docs: List[Document] = []

        for p in pages:
            text = p.get("content") or ""
            if not text.strip():
                continue

            page_no = p.get("pageNumber")

            split_docs = self.splitter.split_text(text=text, document_id=doc_id, page_number=page_no)
            for d in split_docs:
                md = dict(d.metadata or {})
                md.setdefault("filename", filename)
            
                if "chunkId" not in md:
    
                    raise ValueError("Splitter did not assign chunkId.")
                docs.append(Document(page_content=d.page_content, metadata=md))

        docs = self._filter_min_len(docs, self.cfg.min_chars_per_chunk)
        docs_unique = self._dedupe(docs) if self.cfg.dedupe else docs
        if not docs_unique:
            return {"status": "error", "doc_id": doc_id, "reason": "no_usable_chunks_after_split"}

        t1 = time.perf_counter()
        await to_thread.run_sync(self._save_all, docs_unique)
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
                "store_s": round(t_store, 3),
            },
        }
        logger.info(
            "Ingest done doc_id=%s pages=%s chunks=%s stored=%s timings=%s",
            doc_id, len(pages), len(docs_unique), result["stored"], result["timings"]
        )
        return result

    async def _ingest_texts(
        self,
        chunks: List[str],
        doc_id: str,
        base_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Chunk and index pre-supplied plain texts (no PDF)."""
        base_metadata = base_metadata or {}
        docs: List[Document] = []

        t0 = time.perf_counter()
        non_empty_inputs = 0
        produced_before_filter = 0

        for idx, ch in enumerate(chunks, start=1):
            content = (ch or "").strip()
            if not content:
                continue
            non_empty_inputs += 1

            split_docs = self.splitter.split_text(text=content, document_id=doc_id, page_number=None)
            produced_before_filter += len(split_docs)
            for d in split_docs:
                md = dict(d.metadata or {})
                md.update(base_metadata)
                if "chunkId" not in md:
                    raise ValueError("Splitter did not assign chunkId.")
                docs.append(Document(page_content=d.page_content, metadata=md))

        t_split = time.perf_counter() - t0

        before_filter = len(docs)
        docs = self._filter_min_len(docs, self.cfg.min_chars_per_chunk)
        filtered_out = before_filter - len(docs)

        before_dedupe = len(docs)
        docs_unique = self._dedupe(docs) if self.cfg.dedupe else docs
        deduped_out = before_dedupe - len(docs_unique)

        if not docs_unique:
            return {
                "status": "error",
                "doc_id": doc_id,
                "reason": "no_usable_chunks",
                "counters": {
                    "inputs_seen": len(chunks),
                    "inputs_non_empty": non_empty_inputs,
                    "chunks_before_filter": produced_before_filter,
                    "filtered_out": filtered_out,
                    "deduped_out": deduped_out,
                }
            }

        t1 = time.perf_counter()
        await to_thread.run_sync(self._save_all, docs_unique)
        t_store = time.perf_counter() - t1

        result = {
            "status": "success",
            "doc_id": doc_id,
            "chunk_count": len(docs_unique),
            "stored": len(docs_unique),
            "counters": {
                "inputs_seen": len(chunks),
                "inputs_non_empty": non_empty_inputs,
                "chunks_before_filter": produced_before_filter,
                "filtered_out": filtered_out,
                "deduped_out": deduped_out,
            },
            "timings": {
            "split_s": round(t_split, 3),
            "store_s": round(t_store, 3),
            },
        }
        logger.info(
            "Ingest(texts) done doc_id=%s non_empty=%s chunks=%s filtered=%s deduped=%s stored=%s timings=%s",
            doc_id, non_empty_inputs, produced_before_filter, filtered_out, deduped_out,
            result["stored"], result["timings"]
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
            key = hashlib.sha1(_normalize_text(d.page_content).encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            unique.append(d)
        return unique

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=0.8, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )

    def _save_all(self, docs: List[Document]) -> None:
        """
        Synchronous write of all chunks in one call.
        VectorStore will rebuild (delete + recreate) the per-document FAISS index.
        """
        self.vector_store.save_to_faiss(docs=docs)

