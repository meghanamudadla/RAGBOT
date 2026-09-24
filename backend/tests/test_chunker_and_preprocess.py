"""
Unit tests for text preprocessing, extraction, and chunking.
"""
import unittest
from app.ai.preprocess import clean_text
from app.ai.extractors import extract_text, extract_text_from_txt, SUPPORTED_EXTENSIONS
from app.ai.chunker import chunk_text, TextChunk, CHUNK_SIZE, CHUNK_OVERLAP


class TestPreprocessor(unittest.TestCase):
    def test_clean_text_normalizes_whitespace_and_unicode(self):
        raw = "Line 1   \n\n\n\nLine 2 \u00a0 with non-breaking space\n\n\nLine 3"
        cleaned = clean_text(raw)
        # Verify 3+ consecutive blank lines collapsed
        self.assertNotIn("\n\n\n", cleaned)
        # Verify non-breaking space replaced with regular space
        self.assertNotIn("\u00a0", cleaned)
        self.assertIn("Line 1", cleaned)
        self.assertIn("Line 2   with non-breaking space", cleaned)
        self.assertIn("Line 3", cleaned)

    def test_clean_text_empty(self):
        self.assertEqual(clean_text("   \n\n   "), "")


class TestExtractors(unittest.TestCase):
    def test_supported_extensions(self):
        self.assertIn("pdf", SUPPORTED_EXTENSIONS)
        self.assertIn("docx", SUPPORTED_EXTENSIONS)
        self.assertIn("txt", SUPPORTED_EXTENSIONS)

    def test_extract_text_txt_utf8(self):
        sample = "Enterprise RAG Chatbot Document"
        result = extract_text(sample.encode("utf-8"), "txt")
        self.assertEqual(result, sample)

    def test_extract_text_txt_latin1(self):
        sample = "Café au lait"
        result = extract_text(sample.encode("latin-1"), "txt")
        self.assertIn("Caf", result)

    def test_unsupported_extension_raises(self):
        with self.assertRaises(ValueError):
            extract_text(b"some content", "exe")


class TestChunker(unittest.TestCase):
    def test_chunk_short_text(self):
        text = "This is a short document that fits in one chunk."
        chunks = chunk_text(text, source_name="doc.txt")
        self.assertEqual(len(chunks), 1)
        self.assertIsInstance(chunks[0], TextChunk)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[0].metadata["source"], "doc.txt")
        self.assertEqual(chunks[0].metadata["chunk_index"], 0)

    def test_chunk_long_text_overlap(self):
        # Create text exceeding CHUNK_SIZE (1000 chars)
        paragraph = "Artificial intelligence and Retrieval-Augmented Generation enhance document discovery. " * 20
        self.assertGreater(len(paragraph), CHUNK_SIZE)

        chunks = chunk_text(paragraph, source_name="report.pdf")
        self.assertGreater(len(chunks), 1)

        # Check sequential indexing
        for i, c in enumerate(chunks):
            self.assertEqual(c.chunk_index, i)
            self.assertEqual(c.metadata["source"], "report.pdf")


if __name__ == "__main__":
    unittest.main()
