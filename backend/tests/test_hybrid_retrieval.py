"""
Unit tests for hybrid retrieval + reranking pipeline.
"""
import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.ai.bm25_index import BM25Index, _tokenize, get_bm25_index
from app.ai.reranker import reciprocal_rank_fusion, rerank
from app.ai.retriever import Retriever


class TestBM25Index(unittest.TestCase):
    """Tests for BM25 index with per-user isolation."""

    def setUp(self):
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())

    def test_tokenize(self):
        tokens = _tokenize("Hello, World! This is a test.")
        self.assertEqual(tokens, ["hello", "world", "this", "is", "a", "test"])

    def test_upsert_and_query(self):
        index = BM25Index(self.user_a)
        chunk_ids = ["chunk_1", "chunk_2"]
        documents = ["The quick brown fox", "jumps over the lazy dog"]
        metadatas = [
            {"document_id": "doc_1", "chunk_index": 0},
            {"document_id": "doc_1", "chunk_index": 1},
        ]
        index.upsert_chunks(chunk_ids, documents, metadatas)

        # Query for "fox" should return chunk_1 first
        hits = index.query("fox", n_results=2)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["id"], "chunk_1")
        self.assertIn("fox", hits[0]["document"].lower())

    def test_user_isolation(self):
        """User A's query never returns User B's chunks."""
        index_a = BM25Index(self.user_a)
        index_b = BM25Index(self.user_b)

        index_a.upsert_chunks(
            ["a_chunk_1"],
            ["User A secret document"],
            [{"document_id": "doc_a", "user_id": self.user_a}],
        )
        index_b.upsert_chunks(
            ["b_chunk_1"],
            ["User B secret document"],
            [{"document_id": "doc_b", "user_id": self.user_b}],
        )

        # User A queries
        hits_a = index_a.query("secret", n_results=5)
        self.assertEqual(len(hits_a), 1)
        self.assertEqual(hits_a[0]["id"], "a_chunk_1")
        self.assertEqual(hits_a[0]["metadata"]["user_id"], self.user_a)

        # User B queries
        hits_b = index_b.query("secret", n_results=5)
        self.assertEqual(len(hits_b), 1)
        self.assertEqual(hits_b[0]["id"], "b_chunk_1")
        self.assertEqual(hits_b[0]["metadata"]["user_id"], self.user_b)

    def test_delete_by_document_id(self):
        index = BM25Index(self.user_a)
        index.upsert_chunks(
            ["chunk_1", "chunk_2"],
            ["Document one content", "Document two content"],
            [
                {"document_id": "doc_1", "chunk_index": 0},
                {"document_id": "doc_2", "chunk_index": 0},
            ],
        )

        index.delete_by_document_id("doc_1")
        hits = index.query("content", n_results=5)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["id"], "chunk_2")
        self.assertEqual(hits[0]["metadata"]["document_id"], "doc_2")


class TestRRF(unittest.TestCase):
    """Tests for Reciprocal Rank Fusion."""

    def test_rrf_basic_merge(self):
        """RRF merges two lists correctly."""
        list1 = [
            {"id": "a", "document": "doc a", "metadata": {}, "distance": 0.1},
            {"id": "b", "document": "doc b", "metadata": {}, "distance": 0.2},
            {"id": "c", "document": "doc c", "metadata": {}, "distance": 0.3},
        ]
        list2 = [
            {"id": "b", "document": "doc b", "metadata": {}, "distance": 0.15},
            {"id": "d", "document": "doc d", "metadata": {}, "distance": 0.25},
            {"id": "a", "document": "doc a", "metadata": {}, "distance": 0.35},
        ]

        merged = reciprocal_rank_fusion([list1, list2], k=60)

        # a: 1/(60+1) + 1/(60+3) = 0.0161 + 0.0159 = 0.0320
        # b: 1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325
        # c: 1/(60+3) = 0.0159
        # d: 1/(60+2) = 0.0161

        # b should be first (highest RRF score)
        self.assertEqual(merged[0]["id"], "b")
        self.assertEqual(merged[1]["id"], "a")
        self.assertEqual(merged[2]["id"], "d")
        self.assertEqual(merged[3]["id"], "c")

        # All should have rrf_score
        for m in merged:
            self.assertIn("rrf_score", m)

    def test_rrf_single_list(self):
        """RRF works with a single input list."""
        list1 = [
            {"id": "a", "document": "doc a", "metadata": {}, "distance": 0.1},
            {"id": "b", "document": "doc b", "metadata": {}, "distance": 0.2},
        ]
        merged = reciprocal_rank_fusion([list1], k=60)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["id"], "a")
        self.assertEqual(merged[1]["id"], "b")


class TestReranker(unittest.TestCase):
    """Tests for cross-encoder reranker."""

    @patch("app.ai.reranker._load_cross_encoder")
    def test_rerank_changes_order(self, mock_load):
        """Reranker can promote exact keyword match over embedding-similar distractor."""
        # Mock cross-encoder to return higher score for exact match
        mock_encoder = MagicMock()
        # candidate_0: exact keyword match -> high score
        # candidate_1: embedding-similar but irrelevant -> low score
        mock_encoder.predict.return_value = [0.9, 0.1]
        mock_load.return_value = mock_encoder

        candidates = [
            {"id": "c0", "document": "The revenue increased by 15% in Q3", "metadata": {}},
            {"id": "c1", "document": "The revenue decreased by 5% in Q2", "metadata": {}},
        ]

        reranked = rerank("revenue increased 15%", candidates, top_k=2)

        # Exact match (c0) should be first
        self.assertEqual(reranked[0]["id"], "c0")
        self.assertEqual(reranked[1]["id"], "c1")
        self.assertIn("rerank_score", reranked[0])
        self.assertIn("distance", reranked[0])

    @patch("app.ai.reranker._load_cross_encoder")
    def test_rerank_empty_list(self, mock_load):
        """Rerank handles empty input."""
        mock_encoder = MagicMock()
        mock_load.return_value = mock_encoder

        result = rerank("query", [], top_k=5)
        self.assertEqual(result, [])

    @patch("app.ai.reranker._load_cross_encoder")
    def test_rerank_top_k(self, mock_load):
        """Rerank respects top_k limit."""
        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_load.return_value = mock_encoder

        candidates = [
            {"id": f"c{i}", "document": f"doc {i}", "metadata": {}}
            for i in range(5)
        ]

        reranked = rerank("query", candidates, top_k=3)
        self.assertEqual(len(reranked), 3)
        # Highest score should be first
        self.assertEqual(reranked[0]["id"], "c4")


class TestRetrieverHybrid(unittest.TestCase):
    """Tests for Retriever with hybrid retrieval + reranking."""

    def setUp(self):
        self.user_id = str(uuid.uuid4())
        self.query = "revenue results Q3"

    def test_retrieve_returns_correct_shape(self):
        """Retriever.retrieve returns same dict shape as before."""
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = [
            {
                "id": str(uuid.uuid4()),
                "document": "Revenue increased by 15%",
                "metadata": {"user_id": self.user_id, "filename": "financials.pdf", "chunk_index": 0},
                "distance": 0.12,
            }
        ]

        # Mock BM25 index to return empty (so we test dense-only path through hybrid)
        with patch("app.ai.retriever.get_bm25_index") as mock_get_bm25:
            mock_bm25 = MagicMock()
            mock_bm25.query.return_value = []
            mock_get_bm25.return_value = mock_bm25

            # Mock reranker to pass through
            with patch("app.ai.retriever.rerank") as mock_rerank:
                mock_rerank.side_effect = lambda q, c, top_k: c[:top_k]

                with patch("app.ai.retriever.reciprocal_rank_fusion") as mock_rrf:
                    mock_rrf.side_effect = lambda lists, k: lists[0] if lists else []

                    retriever = Retriever(embedding_client=mock_embedder, vector_store=mock_vector_store)
                    results = retriever.retrieve(self.query, self.user_id, top_k=5)

        # Verify return shape
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIn("id", result)
        self.assertIn("document", result)
        self.assertIn("metadata", result)
        self.assertIn("distance", result)
        self.assertEqual(result["metadata"]["user_id"], self.user_id)

    def test_retrieve_calls_both_dense_and_bm25(self):
        """Retriever calls both dense vector store and BM25 index."""
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = [
            {"id": "d1", "document": "dense hit", "metadata": {"user_id": self.user_id}, "distance": 0.1},
        ]

        with patch("app.ai.retriever.get_bm25_index") as mock_get_bm25:
            mock_bm25 = MagicMock()
            mock_bm25.query.return_value = [
                {"id": "b1", "document": "bm25 hit", "metadata": {"user_id": self.user_id}, "distance": -10.0},
            ]
            mock_get_bm25.return_value = mock_bm25

            with patch("app.ai.retriever.rerank") as mock_rerank:
                mock_rerank.side_effect = lambda q, c, top_k: c[:top_k]

                with patch("app.ai.retriever.reciprocal_rank_fusion") as mock_rrf:
                    mock_rrf.side_effect = lambda lists, k: lists[0] + lists[1] if len(lists) > 1 else lists[0]

                    retriever = Retriever(embedding_client=mock_embedder, vector_store=mock_vector_store)
                    retriever.retrieve(self.query, self.user_id, top_k=5)

        # Verify both were called
        mock_vector_store.query.assert_called_once()
        mock_bm25.query.assert_called_once_with(self.query, n_results=20)


if __name__ == "__main__":
    unittest.main()