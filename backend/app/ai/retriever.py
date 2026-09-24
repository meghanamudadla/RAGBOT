"""
Retriever layer for hybrid (dense + BM25) search with cross-encoder reranking.
"""
from app.ai.embeddings import EmbeddingClient
from app.ai.vector_store import VectorStore
from app.ai.bm25_index import get_bm25_index
from app.ai.reranker import reciprocal_rank_fusion, rerank
from app.core.config import settings


class Retriever:
    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        vector_store: VectorStore | None = None,
    ):
        self._embedding_client = embedding_client or EmbeddingClient()
        self._vector_store = vector_store or VectorStore()

    def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[dict]:
        """
        Hybrid retrieval + reranking pipeline:
        1. Dense vector search (top RERANK_CANDIDATE_POOL)
        2. BM25 keyword search (top RERANK_CANDIDATE_POOL)
        3. Reciprocal Rank Fusion (RRF) merge
        4. Cross-encoder rerank top fused candidates
        5. Return top_k with original dict shape (id, document, metadata, distance)
        """
        candidate_pool = settings.RERANK_CANDIDATE_POOL

        # 1. Dense vector search
        query_embedding = self._embedding_client.embed(query)
        dense_hits = self._vector_store.query(
            query_embedding,
            n_results=candidate_pool,
            filter_metadata={"user_id": str(user_id)},
        )

        # 2. BM25 keyword search (per-user isolation)
        bm25_index = get_bm25_index(user_id)
        bm25_hits = bm25_index.query(query, n_results=candidate_pool)

        # 3. RRF merge
        fused = reciprocal_rank_fusion(
            [dense_hits, bm25_hits],
            k=settings.RRF_K,
        )

        # 4. Cross-encoder rerank
        reranked = rerank(query, fused, top_k=top_k)

        # 5. Return in original shape: id, document, metadata, distance
        # distance now reflects cross-encoder score (negated, lower-is-better)
        results = []
        for hit in reranked:
            results.append({
                "id": hit["id"],
                "document": hit["document"],
                "metadata": hit["metadata"],
                "distance": hit["distance"],
            })
        return results
