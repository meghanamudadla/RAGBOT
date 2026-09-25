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
from app.core.config import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

class EmbeddingClient:
    """Thin wrapper around Google GenAI Embeddings to offload memory usage."""

    def __init__(self) -> None:
        self._model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.GEMINI_API_KEY,
        )

    def embed(self, text: str) -> list[float]:
        return self._model.embed_query(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        # langchain natively supports batch embedding
        return self._model.embed_documents(texts)

