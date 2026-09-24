from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = Field(default="AI Document Search")
    DEBUG: bool = Field(default=False)
    # Database
    POSTGRES_DSN: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/docapp")
    # ChromaDB
    CHROMA_PATH: str = Field(default="./chroma")
    # LLM
    GEMINI_API_KEY: str = Field(default="")
    # Google OAuth ("Continue with Google")
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/google/callback")
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    # JWT
    JWT_SECRET_KEY: str = Field(default="change_me_to_a_long_random_secret_32_chars_min")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    # Hybrid Retrieval + Reranking
    RERANK_MODEL_NAME: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    RERANK_CANDIDATE_POOL: int = Field(default=20)
    RRF_K: int = Field(default=60)
    BM25_INDEX_PATH: str = Field(default="")
    # Groundedness Checking
    GROUNDEDNESS_MODEL_NAME: str = Field(default="cross-encoder/nli-deberta-v3-small")
    GROUNDEDNESS_GROUNDED_THRESHOLD: float = Field(default=0.7)
    GROUNDEDNESS_WEAK_THRESHOLD: float = Field(default=0.4)
    GROUNDEDNESS_HIGH_CONFIDENCE_RATIO: float = Field(default=0.8)
    GROUNDEDNESS_LOW_CONFIDENCE_RATIO: float = Field(default=0.5)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate a single settings object for import elsewhere
settings = Settings()

# Derive BM25_INDEX_PATH from CHROMA_PATH if not explicitly set
if not settings.BM25_INDEX_PATH:
    settings.BM25_INDEX_PATH = str(Path(settings.CHROMA_PATH).parent / "bm25_indexes")
