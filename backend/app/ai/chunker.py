"""
Text chunker using LangChain's RecursiveCharacterTextSplitter.

WHY RECURSIVE SPLITTER:
  It tries to split on paragraph breaks first, then sentences, then words.
  This preserves semantic coherence better than fixed-size character splits,
  which can cut mid-sentence and degrade embedding quality.

WHY OVERLAP:
  A sliding overlap ensures that context spanning two chunks isn't lost.
  Without overlap, a question that spans a chunk boundary would find
  neither chunk relevant.
"""
from dataclasses import dataclass
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter


# Tunable constants (centralised here to avoid magic values elsewhere)
CHUNK_SIZE = 1000      # characters per chunk
CHUNK_OVERLAP = 200    # overlap between consecutive chunks


@dataclass
class TextChunk:
    """A single chunk of text with its position metadata."""
    content: str
    chunk_index: int
    metadata: dict  # e.g. {"source": "report.pdf", "char_start": 0}


def chunk_text(text: str, source_name: str = "") -> list[TextChunk]:
    """
    Split cleaned document text into overlapping chunks.

    Args:
        text: Cleaned document text.
        source_name: Original filename for metadata.

    Returns:
        List of TextChunk objects ordered by position.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    raw_chunks = splitter.split_text(text)

    return [
        TextChunk(
            content=chunk,
            chunk_index=i,
            metadata={"source": source_name, "chunk_index": i},
        )
        for i, chunk in enumerate(raw_chunks)
    ]
