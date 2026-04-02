import math
from app.eval.metrics import (
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
)

def test_precision_at_k_basic():
    relevant = ["doc1", "doc2"]
    retrieved = ["doc1", "doc3", "doc2"]
    assert precision_at_k(relevant, retrieved, 1) == 1.0
    assert precision_at_k(relevant, retrieved, 2) == 0.5
    assert precision_at_k(relevant, retrieved, 3) == 2 / 3
    assert precision_at_k(relevant, retrieved, 10) == 2 / 3

def test_recall_at_k_basic():
    relevant = ["doc1", "doc2"]
    retrieved = ["doc1", "doc3", "doc2"]
    assert recall_at_k(relevant, retrieved, 1) == 0.5
    assert recall_at_k(relevant, retrieved, 2) == 0.5
    assert recall_at_k(relevant, retrieved, 3) == 1.0
    assert recall_at_k(relevant, retrieved, 10) == 1.0

def test_mrr_basic():
    relevant = ["doc2"]
    retrieved = ["doc1", "doc2", "doc3"]
    assert mean_reciprocal_rank(relevant, retrieved) == 1 / 2
    assert mean_reciprocal_rank(["doc1"], ["doc1"]) == 1.0
    assert mean_reciprocal_rank(["doc5"], ["doc1", "doc2", "doc3"]) == 0.0

def test_ndcg_at_k_basic():
    relevant = ["doc1", "doc2"]
    retrieved = ["doc1", "doc3", "doc2"]
    idcg = 1 + 1 / math.log2(3)
    dcg = 1 + 1 / math.log2(4)
    expected_ndcg = dcg / idcg
    assert math.isclose(ndcg_at_k(relevant, retrieved, 3), expected_ndcg, rel_tol=1e-6)

def test_edge_cases():
    assert precision_at_k([], [], 5) == 0.0
    assert recall_at_k([], [], 5) == 0.0
    assert mean_reciprocal_rank([], []) == 0.0
    assert ndcg_at_k([], [], 5) == 0.0
