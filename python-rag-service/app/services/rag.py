import asyncio
import logging
import os
from collections import OrderedDict
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import HTTPException
from langchain_core.documents import Document

from app.eval.metrics import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from app.services.open_ai import get_answer_stream_from_openai
from app.services.utils.load_all_chunks import LoadChunksConfig, load_all_chunks
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ==============================================================
# Optional Dependencies
# ==============================================================

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    logger.info("BM25 not available. Falling back to vector search only.")

try:
    from sentence_transformers import CrossEncoder
    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False
    logger.info("CrossEncoder not available. Reranking disabled.")


# ==============================================================
# Hybrid Retrieval Service
# ==============================================================

class HybridRetrievalService:
    """
    Main RAG retrieval service.

    Flow:
      1) Load all chunks for the document.
      2) Run vector search.
      3) Optionally run BM25 search.
      4) Fuse results with Reciprocal Rank Fusion (RRF).
      5) Optionally rerank with a cross-encoder.
      6) Return top-k chunks for answer generation.

    Public APIs:
      - hybrid_retrieve()
      - stream_answer()
      - ask_question()
    """

    def __init__(self):
        """
        Initialize retrieval service with vector store, optional BM25,
        and optional reranker support.
        """
        self.vector_store = VectorStore()
        self.max_retrieval_results = int(os.getenv("MAX_RETRIEVAL_RESULTS", "20"))
        self.final_k = int(os.getenv("FINAL_K", "8"))
        self.use_bm25 = os.getenv("USE_BM25", "true").lower() == "true" and HAS_BM25
        self.use_reranker = os.getenv("USE_RERANKER", "false").lower() == "true" and HAS_CROSS_ENCODER

        self._reranker = None
        self.bm25_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_cache_size = 20

    # --------------------------------------------------------------
    # Reranker loading
    # --------------------------------------------------------------

    async def _load_reranker(self) -> None:
        """
        Lazy-load the cross-encoder reranker once.

        If loading fails, reranking is disabled and retrieval continues
        without it.
        """
        if not self.use_reranker or self._reranker is not None:
            return

        try:
            loop = asyncio.get_event_loop()
            self._reranker = await loop.run_in_executor(
                None,
                CrossEncoder,
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
            )
            logger.info("CrossEncoder loaded successfully")
        except Exception as e:
            logger.warning("Failed to load CrossEncoder: %s", e)
            self.use_reranker = False

    # --------------------------------------------------------------
    # BM25 helpers
    # --------------------------------------------------------------

    def _get_bm25_index(
        self,
        document_id: str,
        documents: List[Document],
    ) -> Optional["BM25Okapi"]:
        """
        Get or build a cached BM25 index for one document.

        Reuses the index when the number of documents has not changed.
        """
        if not self.use_bm25 or not documents:
            return None

        cached = self.bm25_cache.get(document_id)
        if cached and cached["doc_count"] == len(documents):
            self.bm25_cache.move_to_end(document_id)
            return cached["index"]

        try:
            tokenized_corpus = [
                (doc.page_content or "").lower().split()
                for doc in documents
            ]
            index = BM25Okapi(tokenized_corpus)

            self.bm25_cache[document_id] = {
                "index": index,
                "doc_count": len(documents),
            }
            self.bm25_cache.move_to_end(document_id)

            if len(self.bm25_cache) > self.max_cache_size:
                self.bm25_cache.popitem(last=False)

            return index

        except Exception as e:
            logger.warning("BM25 index creation failed: %s", e)
            return None

    # --------------------------------------------------------------
    # Retrieval methods
    # --------------------------------------------------------------

    async def _retrieve_vector_results(
        self,
        question: str,
        document_id: str,
        k: int,
    ) -> List[Document]:
        """
        Retrieve top-k chunks using vector similarity search.

        Adds vector score and vector rank into metadata.
        """
        try:
            loop = asyncio.get_event_loop()
            results_with_scores = await loop.run_in_executor(
                None,
                self.vector_store.similarity_search_with_score,
                document_id,
                question,
                None,
                k,
            )

            results: List[Document] = []
            for rank, (doc, score) in enumerate(results_with_scores, start=1):
                metadata = dict(doc.metadata or {})
                metadata["vec_score"] = float(score)
                metadata["vec_rank"] = rank

                results.append(
                    Document(
                        page_content=doc.page_content,
                        metadata=metadata,
                    )
                )

            return results

        except Exception as e:
            logger.error("Vector retrieval failed: %s", e)
            raise HTTPException(status_code=500, detail="Vector search failed")

    async def _retrieve_bm25_results(
        self,
        question: str,
        document_id: str,
        documents: List[Document],
        k: int,
    ) -> List[Document]:
        """
        Retrieve top-k chunks using BM25 keyword search.

        Adds BM25 score and BM25 rank into metadata.
        """
        if not self.use_bm25 or not documents:
            return []

        try:
            index = self._get_bm25_index(document_id, documents)
            if index is None:
                return []

            query_tokens = question.lower().split()
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, index.get_scores, query_tokens)

            scored_docs = list(zip(scores, documents))
            scored_docs.sort(key=lambda x: x[0], reverse=True)

            results: List[Document] = []
            for rank, (score, doc) in enumerate(scored_docs[:k], start=1):
                if score <= 0:
                    continue

                metadata = dict(doc.metadata or {})
                metadata["bm25_score"] = float(score)
                metadata["bm25_rank"] = rank

                results.append(
                    Document(
                        page_content=doc.page_content,
                        metadata=metadata,
                    )
                )

            return results

        except Exception as e:
            logger.warning("BM25 retrieval failed: %s", e)
            return []

    # --------------------------------------------------------------
    # Fusion and reranking
    # --------------------------------------------------------------

    def _fuse_results_rrf(
        self,
        vector_results: List[Document],
        bm25_results: List[Document],
        rrf_k: int = 60,
    ) -> List[Document]:
        """
        Fuse vector and BM25 results using Reciprocal Rank Fusion (RRF).

        RRF is more stable than directly summing raw scores because
        vector and BM25 scores are not on the same scale.
        """
        fused_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        def add_results(results: List[Document]) -> None:
            for rank, doc in enumerate(results, start=1):
                chunk_id = (doc.metadata or {}).get("chunkId")
                if not chunk_id:
                    continue

                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))

                if chunk_id not in doc_map:
                    doc_map[chunk_id] = doc
                else:
                    existing = doc_map[chunk_id]
                    merged = dict(existing.metadata or {})
                    merged.update(doc.metadata or {})
                    existing.metadata = merged

        add_results(vector_results)
        add_results(bm25_results)

        fused_docs = list(doc_map.values())
        for doc in fused_docs:
            chunk_id = doc.metadata.get("chunkId")
            doc.metadata["fusion_score"] = fused_scores.get(chunk_id, 0.0)

        fused_docs.sort(
            key=lambda d: d.metadata.get("fusion_score", 0.0),
            reverse=True,
        )
        return fused_docs

    async def _rerank_results(
        self,
        question: str,
        documents: List[Document],
    ) -> List[Document]:
        """
        Optionally rerank retrieved chunks with a cross-encoder.

        This is the final ranking step when reranking is enabled.
        """
        if not self.use_reranker or not documents:
            return documents

        await self._load_reranker()
        if self._reranker is None:
            return documents

        try:
            pairs = [(question, doc.page_content or "") for doc in documents]
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, self._reranker.predict, pairs)

            scored_docs = list(zip(scores, documents))
            for score, doc in scored_docs:
                metadata = dict(doc.metadata or {})
                metadata["reranker_score"] = float(score)
                doc.metadata = metadata

            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored_docs]

        except Exception as e:
            logger.warning("Reranking failed: %s", e)
            return documents

    # --------------------------------------------------------------
    # Main hybrid retrieval pipeline
    # --------------------------------------------------------------

    async def hybrid_retrieve(
        self,
        question: str,
        document_id: str,
        ground_truth_ids: Optional[List[str]] = None,
    ) -> List[Document]:
        """
        Run the full hybrid retrieval pipeline for one question.

        Optionally logs retrieval evaluation metrics when ground truth
        chunk IDs are provided.
        """
        try:
            all_chunks = await load_all_chunks(document_id, cfg=LoadChunksConfig(strict=False))
            if not all_chunks:
                logger.warning("No chunks found for document %s", document_id)
                return []

            vector_results = await self._retrieve_vector_results(
                question,
                document_id,
                self.max_retrieval_results,
            )

            if self.use_bm25:
                bm25_results = await self._retrieve_bm25_results(
                    question,
                    document_id,
                    all_chunks,
                    self.max_retrieval_results,
                )
                results = self._fuse_results_rrf(vector_results, bm25_results)
            else:
                results = vector_results

            if self.use_reranker and results:
                results = await self._rerank_results(question, results)

            final_results = results[: self.final_k]

            if ground_truth_ids:
                retrieved_ids = [doc.metadata.get("chunkId") for doc in final_results]
                metrics = {
                    "precision@k": precision_at_k(ground_truth_ids, retrieved_ids, self.final_k),
                    "recall@k": recall_at_k(ground_truth_ids, retrieved_ids, self.final_k),
                    "mrr": mean_reciprocal_rank(ground_truth_ids, retrieved_ids),
                    "ndcg@k": ndcg_at_k(ground_truth_ids, retrieved_ids, self.final_k),
                }
                logger.info("[Eval] document_id=%s question=%r -> %s", document_id, question, metrics)

            return final_results

        except Exception as e:
            logger.exception("hybrid_retrieve failed for document %s: %s", document_id, e)
            return []

    # --------------------------------------------------------------
    # Context and source formatting
    # --------------------------------------------------------------

    async def _build_context(self, chunks: List[Document]) -> str:
        """
        Build a plain-text context block for the LLM from retrieved chunks.
        """
        return "\n\n---\n\n".join(
            (chunk.page_content or "").strip()
            for chunk in chunks
        )

    def _format_sources(self, chunks: List[Document]) -> List[Dict[str, Any]]:
        """
        Format chunk metadata into a frontend-friendly source list.
        """
        sources: List[Dict[str, Any]] = []

        for chunk in chunks:
            metadata = dict(chunk.metadata or {})

            confidence = metadata.get("reranker_score")
            if confidence is None:
                confidence = metadata.get("fusion_score")
            if confidence is None:
                confidence = metadata.get("vec_score")
            if confidence is None:
                confidence = metadata.get("bm25_score")
            if confidence is None:
                confidence = 0.0

            bbox = metadata.get("bbox")
            coordinates = None
            if isinstance(bbox, dict) and all(k in bbox for k in ("x", "y", "width", "height")):
                coordinates = {
                    "x": float(bbox["x"]),
                    "y": float(bbox["y"]),
                    "width": float(bbox["width"]),
                    "height": float(bbox["height"]),
                    "page": int(bbox.get("page", metadata.get("pageNumber") or 1)),
                    "fromPdfSpace": True,
                }

            sources.append(
                {
                    "pageNumber": metadata.get("pageNumber"),
                    "heading": metadata.get("heading"),
                    "textMatch": (chunk.page_content or "")[:200],
                    "confidence": float(confidence),
                    "chunkId": metadata.get("chunkId"),
                    "vec_score": float(metadata.get("vec_score", 0.0)),
                    "bm25_score": float(metadata.get("bm25_score", 0.0)),
                    "reranker_score": float(metadata.get("reranker_score", 0.0)),
                    "fusion_score": float(metadata.get("fusion_score", 0.0)),
                    "coordinates": coordinates,
                }
            )

        return sources

    # --------------------------------------------------------------
    # Public answer APIs
    # --------------------------------------------------------------

    async def stream_answer(
        self,
        question: str,
        document_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream an answer token by token together with sources and source references.
        """
        if not question or not document_id:
            yield {"type": "error", "message": "Question and documentId are required"}
            return

        try:
            chunks = await self.hybrid_retrieve(question, document_id)
            if not chunks:
                yield {"type": "error", "message": "No relevant content found"}
                return

            context = await self._build_context(chunks)
            sources = self._format_sources(chunks)

            yield {"type": "sources", "sources": sources}

            full_answer = ""
            async for token in get_answer_stream_from_openai(context, question):
                full_answer += token
                yield {"type": "answer", "token": token}

            anchor_phrases: List[str] = []
            for line in reversed(full_answer.splitlines()):
                if line.strip().lower().startswith("anchor_phrases:"):
                    raw = line.split(":", 1)[1]
                    anchor_phrases = [p.strip() for p in raw.split("|") if p.strip()]
                    break

            primary_highlight = None
            for chunk in chunks:
                metadata = chunk.metadata or {}
                bbox = metadata.get("bbox")
                if isinstance(bbox, dict) and all(k in bbox for k in ("x", "y", "width", "height")):
                    primary_highlight = {
                        "x": float(bbox["x"]),
                        "y": float(bbox["y"]),
                        "width": float(bbox["width"]),
                        "height": float(bbox["height"]),
                        "page": int(bbox.get("page", metadata.get("pageNumber") or 1)),
                        "fromPdfSpace": True,
                    }
                    break

            yield {
                "type": "source_references",
                "chunkIds": [chunk.metadata.get("chunkId") for chunk in chunks],
                "pageNumbers": sorted(
                    {chunk.metadata.get("pageNumber") for chunk in chunks if chunk.metadata}
                ),
                "fullAnswer": full_answer,
                "anchorPhrases": anchor_phrases,
                "primaryHighlight": primary_highlight,
            }

            yield {"type": "done"}

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error in stream_answer: %s", e)
            yield {"type": "error", "message": "Internal server error"}

    async def ask_question(self, question: str, document_id: str) -> Dict[str, Any]:
        """
        Return a complete non-streaming answer with sources.
        """
        if not question or not document_id:
            raise HTTPException(status_code=400, detail="Question and documentId are required")

        try:
            chunks = await self.hybrid_retrieve(question, document_id)
            if not chunks:
                raise HTTPException(status_code=404, detail="No relevant content found")

            context = await self._build_context(chunks)

            full_answer = ""
            async for token in get_answer_stream_from_openai(context, question):
                full_answer += token

            return {
                "answer": {"text": full_answer},
                "sources": self._format_sources(chunks),
                "documentId": document_id,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error in ask_question: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")


# ==============================================================
# Global instance and exported helpers
# ==============================================================

_qa_instance = None


def get_qa_service() -> HybridRetrievalService:
    """
    Return a singleton instance of the retrieval service.
    """
    global _qa_instance
    if _qa_instance is None:
        _qa_instance = HybridRetrievalService()
    return _qa_instance


async def stream_ask_question(
    question: str,
    document_id: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience wrapper for streaming answers.
    """
    service = get_qa_service()
    async for event in service.stream_answer(question, document_id):
        yield event


async def handle_ask_question(question: str, document_id: str) -> Dict[str, Any]:
    """
    Convenience wrapper for non-streaming answers.
    """
    service = get_qa_service()
    return await service.ask_question(question, document_id)