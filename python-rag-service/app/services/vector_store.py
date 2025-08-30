import os
import shutil
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

log = logging.getLogger(__name__)

# ===============================
# Config
# ===============================

@dataclass
class VectorStoreConfig:
    index_base: str = os.getenv("FAISS_STORE_PATH", "faiss_index")
    k_default: int = 10
    allow_dangerous_deser: bool = True

# ===============================
# Helpers
# ===============================

def _faiss_files_present(path: str) -> bool:
    p = Path(path)
    return (p / "index.faiss").is_file() and (p / "index.pkl").is_file()

# ===============================
# Store
# ===============================

class VectorStore:
    """
    Minimal wrapper around FAISS (via LangChain):

    - Namespaced by model: <index_base>/<embedding_model_sanitized>/
    - Per-document index:  doc_<documentId>/
    - save_to_faiss: builds a fresh index
    """

    def __init__(
        self,
        embedding_model: Optional[str] = None,
        embeddings: Optional[OpenAIEmbeddings] = None,
        cfg: VectorStoreConfig = VectorStoreConfig(),
    ):
        self.cfg = cfg
        self.embeddings = embeddings or OpenAIEmbeddings(
            model=embedding_model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        )
        model_name = embedding_model or getattr(self.embeddings, "model", "openai_embeddings")
        self.model_base_dir = Path(self.cfg.index_base) / embedding_model.replace("/", "_")
        self.model_base_dir.mkdir(parents=True, exist_ok=True)

    def _doc_dir(self, doc_id: str, index_dir: Optional[str] = None) -> Path:
        base = Path(index_dir) if index_dir else self.model_base_dir
        return (base / f"doc_{doc_id}").resolve()

    # ---------------------------
    # Save
    # ---------------------------

    def save_to_faiss(
        self,
        docs: List[Document],
        index_dir: Optional[str] = None,
    ) -> None:
        """
        Build a fresh FAISS index for the given document.

        - Deletes the existing per-document folder (if any).
        - Builds a brand new index from all provided docs.
        """
        if not docs:
            log.info("save_to_faiss: empty docs; nothing to save.")
            return

        doc_id = (docs[0].metadata or {}).get("documentId")
        if not doc_id:
            raise ValueError("First document is missing metadata['documentId'].")

        target_dir = self._doc_dir(str(doc_id), index_dir)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        store = FAISS.from_documents(docs, self.embeddings)
        store.save_local(str(target_dir))
        log.info("Created fresh FAISS index with %d chunks at %s", len(docs), str(target_dir))

    # ---------------------------
    # Load
    # ---------------------------

    def load_faiss_store(
        self,
        document_id: str,
        index_dir: Optional[str] = None,
        as_retriever: bool = True,
        k: Optional[int] = None,
    ):
        """
        Load the FAISS index for a given document_id.
        """
        target_dir = self._doc_dir(str(document_id), index_dir)
        dir_str = str(target_dir)

        if not _faiss_files_present(dir_str):
            raise FileNotFoundError(
                f"FAISS index missing for doc_id={document_id}. "
                f"Expected files at {dir_str}: ['index.faiss','index.pkl']"
            )

        store = FAISS.load_local(
            dir_str,
            self.embeddings,
            allow_dangerous_deserialization=self.cfg.allow_dangerous_deser,
        )

        if not as_retriever:
            return store

        k_eff = int(k or self.cfg.k_default)
        return store.as_retriever(search_kwargs={"k": k_eff})

    # ---------------------------
    # Convenience
    # ---------------------------

    def safe_load_faiss_store(
        self,
        document_id: str,
        index_dir: Optional[str] = None,
        as_retriever: bool = True,
        k: Optional[int] = None,
    ):
        try:
            return self.load_faiss_store(document_id, index_dir=index_dir, as_retriever=as_retriever, k=k)
        except Exception as e:
            log.warning("safe_load_faiss_store: %s", e)
            return None

    def similarity_search(
        self,
        document_id: str,
        query: str,
        index_dir: Optional[str] = None,
        k: Optional[int] = None,
    ) -> List[Document]:
        retr = self.load_faiss_store(document_id, index_dir=index_dir, as_retriever=True, k=k)
        return retr.get_relevant_documents(query)
