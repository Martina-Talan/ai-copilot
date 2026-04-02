from typing import List, Union, Optional, Iterable, Dict, Any, Set
import asyncio
import logging
from dataclasses import dataclass

from langchain_core.documents import Document
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


# ===============================
# Config
# ===============================

@dataclass(frozen=True)
class LoadChunksConfig:
    """
    Configuration for loading chunks from FAISS.

    index_dir:            Optional base directory override for FAISS indices.
    max_items:            Optional hard cap on the number of returned chunks (after sort).
    dedupe_by_chunk_id:   Remove duplicates that share the same `metadata['chunkId']`.
    strict:               If True, raise when index is missing; otherwise return [].
    """
    index_dir: Optional[str] = None
    max_items: Optional[int] = None
    dedupe_by_chunk_id: bool = True
    strict: bool = False

# --------------------------------
# Main
# --------------------------------

async def load_all_chunks(
    document_id: Union[int, str],
    *,
    cfg: Optional[LoadChunksConfig] = None,
) -> List[Document]:
    """
    Load every chunk (LangChain `Document`) for a given `document_id` from the FAISS store.

    Behavior:
      - Opens the FAISS index via `VectorStore.safe_load_faiss_store`.
      - Reads raw documents from the underlying docstore (no embedding queries).
      - Optionally de-duplicates by `chunkId`.
      - Sorts chunks by (pageNumber, heading, chunkId) and applies `max_items` cap.
      - If the FAISS index is missing:
          * strict=True  -> raises FileNotFoundError
          * strict=False -> returns [] and logs a warning
    """
    cfg = cfg or LoadChunksConfig()
    doc_id = str(document_id)

    vs = VectorStore()
    store = vs.safe_load_faiss_store(
        document_id=doc_id,
        index_dir=cfg.index_dir,
        as_retriever=False,
    )

    if store is None:
        msg = f"FAISS index not found for doc_id={doc_id}"
        if cfg.strict:
            logger.error("%s (strict=True) — raising", msg)
            raise FileNotFoundError(msg)
        logger.warning("%s (strict=False) — returning []", msg)
        return []

    def _read_all_from_docstore() -> List[Document]:
        ds = getattr(store, "docstore", None)
        raw_iter: Iterable = ()
        if ds is not None:
   
            if hasattr(ds, "_dict") and isinstance(ds._dict, dict):
                raw_iter = ds._dict.values()
            elif hasattr(ds, "_docs") and isinstance(ds._docs, dict):
                raw_iter = ds._docs.values()

        out: List[Document] = []
        for d in raw_iter:
            try:
                md: Dict[str, Any] = getattr(d, "metadata", {}) or {}
                if str(md.get("documentId")) == doc_id:
                    out.append(d)
            except Exception:
                continue
        return out

    try:
        from anyio import to_thread
        docs = await to_thread.run_sync(_read_all_from_docstore)
    except Exception:
        loop = asyncio.get_event_loop()
        docs = await loop.run_in_executor(None, _read_all_from_docstore)

    if cfg.dedupe_by_chunk_id:
        seen: Set[str] = set()
        uniq: List[Document] = []
        for d in docs:
            cid = str((d.metadata or {}).get("chunkId") or "")
            if cid and cid in seen:
                continue
            if cid:
                seen.add(cid)
            uniq.append(d)
        docs = uniq

    docs.sort(
        key=lambda d: (
            (d.metadata or {}).get("pageNumber") or 0,
            (d.metadata or {}).get("heading") or "",
            (d.metadata or {}).get("chunkId") or "",
        )
    )

    if isinstance(cfg.max_items, int) and cfg.max_items >= 0:
        docs = docs[:cfg.max_items]

    logger.info("Loaded %d chunks for doc_id=%s (faiss)", len(docs), doc_id)
    return docs
