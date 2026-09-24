"""
Unit tests for groundedness checking.
"""
import unittest
from unittest.mock import MagicMock, patch

from app.ai.groundedness import check_groundedness, _split_sentences, _extract_citation_ids, _is_connective_sentence


class TestSentenceSplitting(unittest.TestCase):
    """Tests for sentence splitting utility."""

    def test_split_simple_sentences(self):
        text = "This is the first sentence. This is the second sentence."
        sentences = _split_sentences(text)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0], "This is the first sentence.")
        self.assertEqual(sentences[1], "This is the second sentence.")

    def test_split_with_exclamation_question(self):
        text = "Hello world! How are you? I am fine."
        sentences = _split_sentences(text)
        self.assertEqual(len(sentences), 3)

    def test_empty_text(self):
        sentences = _split_sentences("")
        self.assertEqual(sentences, [])

    def test_whitespace_only(self):
        sentences = _split_sentences("   ")
        self.assertEqual(sentences, [])

    def test_short_fragments_filtered(self):
        # Very short fragments should be filtered out
        text = "This is a sentence. A. This is another."
        sentences = _split_sentences(text)
        # "A." is too short, should be filtered
        self.assertEqual(len(sentences), 2)


class TestCitationExtraction(unittest.TestCase):
    """Tests for citation ID extraction."""

    def test_single_citation(self):
        sentence = "This is a claim [1]."
        ids = _extract_citation_ids(sentence)
        self.assertEqual(ids, [1])

    def test_multiple_citations(self):
        sentence = "This is a claim [1, 2]."
        ids = _extract_citation_ids(sentence)
        self.assertEqual(ids, [1, 2])

    def test_multiple_separate_citations(self):
        sentence = "First claim [1]. Second claim [2]."
        ids = _extract_citation_ids(sentence)
        self.assertEqual(ids, [1, 2])

    def test_no_citations(self):
        sentence = "This is a claim with no citations."
        ids = _extract_citation_ids(sentence)
        self.assertEqual(ids, [])

    def test_spaced_citations(self):
        sentence = "Claim [ 1 , 2 , 3 ]."
        ids = _extract_citation_ids(sentence)
        self.assertEqual(ids, [1, 2, 3])


class TestConnectiveSentence(unittest.TestCase):
    """Tests for connective sentence detection."""

    def test_colon_ending(self):
        self.assertTrue(_is_connective_sentence("Here is a summary:"))
        self.assertTrue(_is_connective_sentence("In conclusion:"))
        self.assertTrue(_is_connective_sentence("To summarize:"))

    def test_connective_phrases(self):
        self.assertTrue(_is_connective_sentence("Here is the answer."))
        self.assertTrue(_is_connective_sentence("In summary, the results show."))
        self.assertTrue(_is_connective_sentence("Overall, this is the case."))
        self.assertTrue(_is_connective_sentence("Note that this is important."))

    def test_regular_sentences(self):
        self.assertFalse(_is_connective_sentence("The revenue increased by 15%."))
        self.assertFalse(_is_connective_sentence("According to the document, sales grew."))
        self.assertFalse(_is_connective_sentence("This is a factual statement about data."))


class TestGroundedness(unittest.TestCase):
    """Tests for check_groundedness function."""

    def setUp(self):
        self.hits = [
            {"document": "Revenue increased by 15% in Q3 2024.", "metadata": {"filename": "financials.pdf"}},
            {"document": "Operating costs decreased by 5% year over year.", "metadata": {"filename": "financials.pdf"}},
            {"document": "The company launched a new product line in March.", "metadata": {"filename": "press.pdf"}},
        ]

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_paraphrase_scores_grounded(self, mock_load):
        """A sentence that closely paraphrases its cited chunk should score as grounded."""
        mock_model = MagicMock()
        # High entailment score for supported claim
        mock_model.predict.return_value = [[0.1, 0.2, 0.85]]  # [contradiction, neutral, entailment]
        mock_load.return_value = mock_model

        answer = "Revenue grew by 15% in the third quarter [1]."
        result = check_groundedness(answer, self.hits)

        self.assertEqual(result["overall_confidence"], "high")
        self.assertEqual(len(result["sentences"]), 1)
        self.assertEqual(result["sentences"][0]["status"], "grounded")
        self.assertEqual(result["sentences"][0]["citation_ids"], [1])
        self.assertGreaterEqual(result["sentences"][0]["score"], 0.7)

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_unrelated_scores_unsupported(self, mock_load):
        """A sentence with no relation to cited chunk should score as unsupported."""
        mock_model = MagicMock()
        # Low entailment score for unsupported claim
        mock_model.predict.return_value = [[0.7, 0.2, 0.1]]  # high contradiction
        mock_load.return_value = mock_model

        answer = "The company went bankrupt in 2023 [1]."
        result = check_groundedness(answer, self.hits)

        self.assertEqual(result["sentences"][0]["status"], "unsupported")
        self.assertLess(result["sentences"][0]["score"], 0.4)

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_no_citation_flagged_unsupported(self, mock_load):
        """A sentence with no citation markers and non-trivial content should be flagged."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        answer = "The company revenue increased by 15%."
        result = check_groundedness(answer, self.hits)

        self.assertEqual(result["sentences"][0]["status"], "unsupported")
        self.assertEqual(result["sentences"][0]["citation_ids"], [])
        self.assertEqual(result["sentences"][0]["score"], 0.0)

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_connective_sentence_skipped(self, mock_load):
        """Connective/filler sentences should be skipped, not flagged."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        answer = "Here is a summary: Revenue increased by 15% [1]."
        result = check_groundedness(answer, self.hits)

        # Should have 2 sentences: one skipped, one grounded
        self.assertEqual(len(result["sentences"]), 2)
        self.assertEqual(result["sentences"][0]["status"], "skipped")
        self.assertEqual(result["sentences"][1]["status"], "grounded")

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_empty_hits(self, mock_load):
        """Empty hits list should return low confidence."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        answer = "Some answer."
        result = check_groundedness(answer, [])

        self.assertEqual(result["overall_confidence"], "low")
        self.assertEqual(result["sentences"], [])

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_empty_answer(self, mock_load):
        """Empty answer should return low confidence."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        result = check_groundedness("", self.hits)

        self.assertEqual(result["overall_confidence"], "low")
        self.assertEqual(result["sentences"], [])

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_mixed_confidence_overall_medium(self, mock_load):
        """Mix of grounded and unsupported should yield medium confidence."""
        mock_model = MagicMock()
        # First call: high score (grounded), second call: low score (unsupported)
        mock_model.predict.side_effect = [
            [[0.1, 0.2, 0.85]],  # grounded
            [[0.7, 0.2, 0.1]],   # unsupported
        ]
        mock_load.return_value = mock_model

        answer = "Revenue grew by 15% [1]. The company went bankrupt [1]."
        result = check_groundedness(answer, self.hits)

        # 1 grounded, 1 unsupported = 50% grounded ratio = medium (between 0.5 and 0.8)
        self.assertEqual(result["overall_confidence"], "medium")

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_multiple_citations_uses_max_score(self, mock_load):
        """When multiple citations, should use max score across all cited chunks."""
        mock_model = MagicMock()
        # First citation low, second citation high
        mock_model.predict.side_effect = [
            [[0.7, 0.2, 0.1]],  # citation 1: low
            [[0.1, 0.2, 0.9]],  # citation 2: high
        ]
        mock_load.return_value = mock_model

        answer = "Revenue grew [1, 2]."
        result = check_groundedness(answer, self.hits)

        # Should use max score (0.9) -> grounded
        self.assertEqual(result["sentences"][0]["status"], "grounded")

    @patch("app.ai.groundedness._load_groundedness_model")
    def test_weak_classification(self, mock_load):
        """Scores between weak and grounded thresholds should be 'weak'."""
        mock_model = MagicMock()
        # Score between 0.4 and 0.7
        mock_model.predict.return_value = [[0.2, 0.4, 0.55]]
        mock_load.return_value = mock_model

        answer = "Revenue somewhat increased [1]."
        result = check_groundedness(answer, self.hits)

        self.assertEqual(result["sentences"][0]["status"], "weak")


class TestWorkflowIntegration(unittest.TestCase):
    """Test that workflow.py verify_node integrates correctly."""

    @patch("app.ai.workflow.check_groundedness")
    def test_verify_node_adds_groundedness(self, mock_check):
        from app.ai.workflow import verify_node

        mock_check.return_value = {
            "overall_confidence": "high",
            "sentences": [{"text": "Test", "citation_ids": [1], "status": "grounded", "score": 0.9}]
        }

        state = {
            "response": "Test answer [1].",
            "context_chunks": [{"document": "Test doc", "metadata": {}}],
        }

        result = verify_node(state)
        self.assertIn("groundedness", result)
        self.assertEqual(result["groundedness"]["overall_confidence"], "high")
        mock_check.assert_called_once_with("Test answer [1].", [{"document": "Test doc", "metadata": {}}])


if __name__ == "__main__":
    unittest.main()