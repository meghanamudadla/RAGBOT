"""
Unit tests for tenant isolation in retrieval.
"""
import unittest
import uuid
from unittest.mock import MagicMock, patch
from app.ai.retriever import Retriever


class TestRetrieverIsolation(unittest.TestCase):
    def test_retrieve_filters_by_user_id(self):
        user_a = uuid.uuid4()
        query = "Explain revenue results"

        # Mock embedding client and vector store
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = [
            {
                "id": str(uuid.uuid4()),
                "document": "Revenue increased by 15%",
                "metadata": {"user_id": str(user_a), "filename": "financials.pdf", "chunk_index": 0},
                "distance": 0.12,
            }
        ]

        # Mock BM25 index to return empty
        with patch("app.ai.retriever.get_bm25_index") as mock_get_bm25:
            mock_bm25 = MagicMock()
            mock_bm25.query.return_value = []
            mock_get_bm25.return_value = mock_bm25

            # Mock reranker and RRF to pass through
            with patch("app.ai.retriever.rerank") as mock_rerank:
                mock_rerank.side_effect = lambda q, c, top_k: c[:top_k]
                with patch("app.ai.retriever.reciprocal_rank_fusion") as mock_rrf:
                    mock_rrf.side_effect = lambda lists, k: lists[0] if lists else []

                    retriever = Retriever(embedding_client=mock_embedder, vector_store=mock_vector_store)
                    results = retriever.retrieve(query, str(user_a), top_k=5)

        # 1. Verify embed was called with user query
        mock_embedder.embed.assert_called_once_with(query)

        # 2. Verify query was called with strict filter_metadata={"user_id": str(user_a)}
        # Note: n_results is now RERANK_CANDIDATE_POOL (default 20), not top_k
        mock_vector_store.query.assert_called_once()
        call_args = mock_vector_store.query.call_args
        self.assertEqual(call_args.kwargs["filter_metadata"], {"user_id": str(user_a)})
        self.assertEqual(call_args.kwargs["n_results"], 20)  # RERANK_CANDIDATE_POOL default

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["user_id"], str(user_a))


if __name__ == "__main__":
    unittest.main()
