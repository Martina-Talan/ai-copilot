import math
import logging
from typing import Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

# ==============================================================
# Internal Utilities
# ==============================================================

def _dedupe_preserve_order(xs: Iterable[str]) -> List[str]:
    """
    Remove duplicates while preserving order and filtering out empty IDs.
    
    Args:
        xs (Iterable[str]): Input list of IDs.
    
    Returns:
        List[str]: Deduplicated and ordered list.
    """
    seen: Set[str] = set()
    out: List[str] = []
    for x in xs:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def _effective_k(k: Optional[int], n: int) -> int:
    """
    Ensure that 0 ≤ k ≤ n. If k is None or ≤ 0, returns 0.
    
    Args:
        k (Optional[int]): Target rank.
        n (int): Total number of results.
    
    Returns:
        int: Clipped k value.
    """
    if k is None or k <= 0:
        return 0
    return min(k, n)

# ==============================================================
# Evaluation Metrics
# ==============================================================

def precision_at_k(relevant_ids: Iterable[str], retrieved_ids: Iterable[str], k: Optional[int]) -> float:
    """
    Precision@k = (# relevant items in Top-k) / k

    Args:
        relevant_ids (Iterable[str]): Ground truth relevant document IDs.
        retrieved_ids (Iterable[str]): Retrieved document IDs (will be deduplicated).
        k (Optional[int]): Number of top results to consider.

    Returns:
        float: Precision at rank k.
    """
    try:
        retrieved = _dedupe_preserve_order(retrieved_ids or [])
        k_eff = _effective_k(k, len(retrieved))
        if k_eff == 0:
            return 0.0
        rel: Set[str] = set(relevant_ids or [])
        top_k = retrieved[:k_eff]
        hits = sum(1 for doc_id in top_k if doc_id in rel)
        return hits / float(k_eff)
    except Exception as e:
        logger.exception("Failed to compute precision@k: %s", str(e))
        return 0.0

def recall_at_k(relevant_ids: Iterable[str], retrieved_ids: Iterable[str], k: Optional[int]) -> float:
    """
    Recall@k = (# relevant items in Top-k) / (# total relevant items)

    Args:
        relevant_ids (Iterable[str]): Ground truth relevant document IDs.
        retrieved_ids (Iterable[str]): Retrieved document IDs.
        k (Optional[int]): Number of top results to consider.

    Returns:
        float: Recall at rank k.
    """
    try:
        rel: Set[str] = set(relevant_ids or [])
        if not rel:
            return 0.0
        retrieved = _dedupe_preserve_order(retrieved_ids or [])
        k_eff = _effective_k(k, len(retrieved))
        top_k = retrieved[:k_eff]
        hits = sum(1 for doc_id in top_k if doc_id in rel)
        return hits / float(len(rel))
    except Exception as e:
        logger.exception("Failed to compute recall@k: %s", str(e))
        return 0.0

def mean_reciprocal_rank(relevant_ids: Iterable[str], retrieved_ids: Iterable[str]) -> float:
    """
    Mean Reciprocal Rank = 1 / rank of first relevant item in the retrieved list.

    Args:
        relevant_ids (Iterable[str]): Ground truth relevant document IDs.
        retrieved_ids (Iterable[str]): Retrieved document IDs.

    Returns:
        float: MRR score.
    """
    try:
        rel: Set[str] = set(relevant_ids or [])
        if not rel:
            return 0.0
        retrieved = _dedupe_preserve_order(retrieved_ids or [])
        for idx, doc_id in enumerate(retrieved, start=1):
            if doc_id in rel:
                return 1.0 / float(idx)
        return 0.0
    except Exception as e:
        logger.exception("Failed to compute MRR: %s", str(e))
        return 0.0

def ndcg_at_k(relevant_ids: Iterable[str], retrieved_ids: Iterable[str], k: Optional[int]) -> float:
    """
    Normalized Discounted Cumulative Gain (NDCG) at k (binary relevance).
    
    DCG@k  = Σ_i (rel_i / log2(i+2))
    IDCG@k = Ideal DCG (sorted relevance)
    NDCG@k = DCG@k / IDCG@k

    Args:
        relevant_ids (Iterable[str]): Ground truth relevant document IDs.
        retrieved_ids (Iterable[str]): Retrieved document IDs.
        k (Optional[int]): Number of top results to consider.

    Returns:
        float: NDCG score.
    """
    try:
        rel: Set[str] = set(relevant_ids or [])
        retrieved = _dedupe_preserve_order(retrieved_ids or [])
        k_eff = _effective_k(k, len(retrieved))
        if k_eff == 0:
            return 0.0

        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k_eff]):
            if doc_id in rel:
                dcg += 1.0 / math.log2(i + 2.0)

        ideal_hits = min(k_eff, len(rel))
        if ideal_hits == 0:
            return 0.0
        idcg = sum(1.0 / math.log2(i + 2.0) for i in range(ideal_hits))

        return dcg / idcg if idcg > 0.0 else 0.0
    except Exception as e:
        logger.exception("Failed to compute NDCG@k: %s", str(e))
        return 0.0
