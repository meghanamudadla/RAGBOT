"""
BM25 keyword search index with per-user isolation.

WHY BM25:
  - Dense embeddings miss exact keyword matches (e.g., error codes, product IDs).
  - BM25 complements dense search by scoring on term frequency / inverse document frequency.

DESIGN:
  - One BM25Okapi index per user_id (scoped isolation).
  - Tokenized chunks stored as lists of lowercase tokens.
  - Persisted to disk as pickled token lists per user (lightweight, no external deps).
  - Incremental updates: on upsert, append tokens; on delete, rebuild user's index from remaining chunks.
"""
import pickle
import os
from pathlib import Path
from typing import Any
from functools import lru_cache

from rank_bm25 import BM25Okapi

from app.core.config import settings


BM25_INDEX_DIR = Path(settings.BM25_INDEX_PATH)
BM25_INDEX_DIR.mkdir(parents=True, exist_ok=True)


def _get_user_index_path(user_id: str) -> Path:
    """Return the pickle file path for a given user's BM25 index."""
    safe_id = user_id.replace("-", "_")
    return BM25_INDEX_DIR / f"user_{safe_id}.pkl"


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenization (lowercased)."""
    import re
    return re.findall(r"\w+", text.lower())


class BM25Index:
    """
    Per-user BM25 keyword index.

    Each instance manages one user's index. The index is loaded from disk on init
    and saved back on every mutation (upsert/delete). For low-to-medium document
    counts this is fast enough; for very large corpora a more sophisticated
    incremental index would be needed.
    """

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._index_path = _get_user_index_path(user_id)
        self._tokenized_chunks: dict[str, list[str]] = {}  # chunk_id -> tokens
        self._chunk_texts: dict[str, str] = {}             # chunk_id -> original text
        self._chunk_metadata: dict[str, dict] = {}         # chunk_id -> metadata
        self._bm25: BM25Okapi | None = None
        self._load()

    def _load(self) -> None:
        """Load tokenized chunks from disk and rebuild BM25Okapi."""
        if self._index_path.exists():
            with open(self._index_path, "rb") as f:
                data = pickle.load(f)
                self._tokenized_chunks = data.get("tokens", {})
                self._chunk_texts = data.get("texts", {})
                self._chunk_metadata = data.get("metadata", {})
        self._rebuild()

    def _save(self) -> None:
        """Persist tokenized chunks and metadata to disk."""
        data = {
            "tokens": self._tokenized_chunks,
            "texts": self._chunk_texts,
            "metadata": self._chunk_metadata,
        }
        with open(self._index_path, "wb") as f:
            pickle.dump(data, f)

    def _rebuild(self) -> None:
        """Rebuild BM25Okapi from current tokenized chunks."""
        if self._tokenized_chunks:
            self._bm25 = BM25Okapi(list(self._tokenized_chunks.values()))
        else:
            self._bm25 = None

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add or update chunks in the index."""
        for chunk_id, doc, meta in zip(chunk_ids, documents, metadatas):
            self._tokenized_chunks[chunk_id] = _tokenize(doc)
            self._chunk_texts[chunk_id] = doc
            self._chunk_metadata[chunk_id] = meta
        self._rebuild()
        self._save()

    def delete_by_document_id(self, document_id: str) -> None:
        """Remove all chunks belonging to a document_id."""
        to_remove = [
            cid for cid, meta in self._chunk_metadata.items()
            if meta.get("document_id") == document_id
        ]
        for cid in to_remove:
            self._tokenized_chunks.pop(cid, None)
            self._chunk_texts.pop(cid, None)
            self._chunk_metadata.pop(cid, None)
        if to_remove:
            self._rebuild()
            self._save()

    def query(self, query_text: str, n_results: int = 20) -> list[dict]:
        """
        BM25 search over this user's chunks.

        Returns list of dicts with keys: id, document, metadata, distance (BM25 score, negated for lower-is-better).
        """
        if not self._bm25 or not self._tokenized_chunks:
            return []

        query_tokens = _tokenize(query_text)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        chunk_ids = list(self._tokenized_chunks.keys())

        # Pair (chunk_id, score) and sort by score descending (higher BM25 = better)
        ranked = sorted(zip(chunk_ids, scores), key=lambda x: x[1], reverse=True)

        hits = []
        for rank, (chunk_id, score) in enumerate(ranked[:n_results]):
            hits.append({
                "id": chunk_id,
                "document": self._chunk_texts[chunk_id],
                "metadata": self._chunk_metadata[chunk_id],
                "distance": -score,  # negate so lower-is-better (like dense distance)
                "bm25_score": score,
                "rank": rank,
            })
        return hits


@lru_cache(maxsize=128)
def _get_bm25_index(user_id: str) -> BM25Index:
    """Cache BM25Index instances per user_id."""
    return BM25Index(user_id)


def get_bm25_index(user_id: str) -> BM25Index:
    """Public accessor for a user's BM25 index."""
    return _get_bm25_index(user_id)