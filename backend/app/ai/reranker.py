"""
Cross-encoder reranker and Reciprocal Rank Fusion (RRF) utilities.

WHY CROSS-ENCODER:
  - Dense retrieval (bi-encoder) is fast but less accurate on nuanced queries.
  - Cross-encoder attends to query+doc jointly, giving better relevance scores.
  - Used as a second stage on a small candidate pool (fast + accurate).

WHY RRF:
  - Merges ranked lists from dense + BM25 without needing calibrated scores.
  - Parameter-free (k=60 default), robust, widely used in IR.
"""
from functools import lru_cache
from typing import Any

from app.core.config import settings


@lru_cache(maxsize=1)
def _load_cross_encoder():
    """Load cross-encoder model once and cache for process lifetime."""
    from sentence_transformers import CrossEncoder
    return CrossEncoder(settings.RERANK_MODEL_NAME, device="cpu")


def get_cross_encoder():
    """Public accessor for the cross-encoder model."""
    return _load_cross_encoder()


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Rerank candidates using cross-encoder.

    Args:
        query: User query string.
        candidates: List of dicts with at least 'id', 'document', 'metadata'.
        top_k: Number of results to return.

    Returns:
        Top-k candidates sorted by cross-encoder score (descending).
        Adds 'rerank_score' (raw cross-encoder logit) and 'distance' (negated score for lower-is-better).
    """
    if not candidates:
        return []

    cross_encoder = get_cross_encoder()
    pairs = [(query, c["document"]) for c in candidates]
    scores = cross_encoder.predict(pairs, show_progress_bar=False)

    # Attach scores and sort descending
    for cand, score in zip(candidates, scores):
        cand["rerank_score"] = float(score)
        cand["distance"] = -float(score)  # lower-is-better convention

    reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return reranked[:top_k]


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion (RRF).

    Args:
        ranked_lists: List of ranked candidate lists. Each candidate dict must have 'id'.
        k: RRF constant (default 60).

    Returns:
        Merged candidates sorted by RRF score descending.
        Adds 'rrf_score' to each candidate.
    """
    rrf_scores: dict[str, float] = {}
    candidate_map: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, candidate in enumerate(ranked_list):
            cid = candidate["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            # Keep the first occurrence's data (they should be identical across lists)
            if cid not in candidate_map:
                candidate_map[cid] = candidate.copy()

    # Build merged list with RRF scores
    merged = []
    for cid, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        cand = candidate_map[cid]
        cand["rrf_score"] = score
        merged.append(cand)

    return merged