"""
ChromaDB vector store wrapper.

WHY CHROMA:
  - Runs fully locally with no external service required.
  - Persistent client stores embeddings to disk across restarts.
  - Supports metadata filtering (e.g. filter by user_id or document_id).

WHY ONE COLLECTION PER APP (NOT PER USER):
  - A single shared collection with metadata filtering is more efficient
    than creating many small per-user collections.
  - Multi-tenant isolation is enforced via the `user_id` metadata field.

DESIGN NOTE:
  We use chunk UUIDs (string) as Chroma document IDs. This means the
  same chunk is never stored twice and deletion is O(1) by ID.
"""
from functools import lru_cache
from app.core.config import settings

COLLECTION_NAME = "document_chunks"


@lru_cache(maxsize=1)
def _get_chroma_client():
    """Initialise and cache a persistent ChromaDB client."""
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    return chromadb.PersistentClient(
        path=settings.CHROMA_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )



class VectorStore:
    """Manages upsert, query, and deletion of document chunk embeddings."""

    def __init__(self) -> None:
        client = _get_chroma_client()
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # use cosine similarity
        )

    def upsert_chunks(
        self,
        chunk_ids: list[str],         # UUID strings (match DB chunk.id)
        embeddings: list[list[float]],
        documents: list[str],         # raw chunk text (for Chroma's storage)
        metadatas: list[dict],        # must include document_id, user_id, chunk_index
    ) -> None:
        """Add or update a batch of chunk embeddings."""
        self._collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        """
        Semantic search over stored chunks.

        Returns a list of dicts with keys:
          id, document (text), metadata, distance
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i, chunk_id in enumerate(results["ids"][0]):
            hits.append({
                "id": chunk_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return hits

    def delete_by_document_id(self, document_id: str) -> None:
        """Remove all chunks belonging to a document (called on document delete)."""
        self._collection.delete(where={"document_id": document_id})
