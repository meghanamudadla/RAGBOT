"""
HuggingFace sentence-transformers embedding client.

WHY HUGGINGFACE EMBEDDINGS:
  - Completely free and runs locally — no API cost per document.
  - `all-MiniLM-L6-v2` is fast (22M params) and produces high-quality
    384-dim embeddings suitable for semantic search.
  - The model is downloaded once and cached by sentence-transformers.

WHY A WRAPPER CLASS:
  Decouples the rest of the codebase from the specific embedding library.
  Swapping to OpenAI or Cohere embeddings later requires only changing
  this file, not the chunker, vector store, or retriever.
"""
from functools import lru_cache

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model():
    """Load model once and cache for the lifetime of the process."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")



class EmbeddingClient:
    """Thin wrapper around SentenceTransformer for embedding text."""

    def __init__(self) -> None:
        self._model = _load_model()

    def embed(self, text: str) -> list[float]:
        """Embed a single string and return a list of floats."""
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed multiple texts in batches for efficiency.
        normalize_embeddings=True makes cosine similarity equal to dot product,
        which ChromaDB uses internally.
        """
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]
