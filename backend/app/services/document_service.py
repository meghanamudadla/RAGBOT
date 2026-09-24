"""
DocumentService — orchestrates the full ingestion pipeline.

Pipeline:
  uploaded file bytes
    → extract text          (extractors.py)
    → clean text            (preprocess.py)
    → chunk text            (chunker.py)
    → embed chunks          (embeddings.py)
    → persist chunks in DB  (ChunkRepository via DocumentRepository)
    → store vectors         (vector_store.py)
    → store BM25 tokens     (bm25_index.py)
    → return DocumentResponse
"""
import uuid
from pathlib import Path
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.extractors import extract_text, SUPPORTED_EXTENSIONS
from app.ai.preprocess import clean_text
from app.ai.chunker import chunk_text
from app.ai.embeddings import EmbeddingClient
from app.ai.vector_store import VectorStore
from app.ai.bm25_index import get_bm25_index
from app.db.models.document import Document
from app.db.models.chunk import Chunk
from app.repositories.document_repository import DocumentRepository
from app.repositories.base_repository import BaseRepository
from app.db.models.chunk import Chunk as ChunkModel
from app.schemas.document import DocumentResponse


class DocumentService:
    def __init__(
        self,
        db: AsyncSession,
        embedding_client: EmbeddingClient | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._doc_repo = DocumentRepository(db)
        self._chunk_repo: BaseRepository[ChunkModel] = BaseRepository(ChunkModel, db)
        self._embedder = embedding_client or EmbeddingClient()
        self._vector_store = vector_store or VectorStore()

    async def upload_document(
        self, file: UploadFile, user_id: uuid.UUID
    ) -> DocumentResponse:
        # 1. Validate extension
        suffix = Path(file.filename or "").suffix.lstrip(".")
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '.{suffix}'. Allowed: {SUPPORTED_EXTENSIONS}",
            )

        # 2. Read bytes
        file_bytes = await file.read()

        # 3. Extract & clean text
        raw_text = extract_text(file_bytes, suffix)
        cleaned = clean_text(raw_text)

        if not cleaned.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract any text from the uploaded file.",
            )

        # 4. Persist Document record
        doc = Document(
            user_id=user_id,
            filename=file.filename or "unknown",
            file_type=suffix,
        )
        doc = await self._doc_repo.create(doc)

        # 5. Chunk text
        chunks = chunk_text(cleaned, source_name=file.filename or "")

        # 6. Embed all chunks in a single batch
        texts = [c.content for c in chunks]
        embeddings = self._embedder.embed_batch(texts)

        # 7. Persist Chunk records in DB
        db_chunks: list[ChunkModel] = []
        for chunk, embedding in zip(chunks, embeddings):
            db_chunk = ChunkModel(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata_=chunk.metadata,
            )
            db_chunk = await self._chunk_repo.create(db_chunk)
            db_chunks.append(db_chunk)

        # 8. Store vectors in ChromaDB
        self._vector_store.upsert_chunks(
            chunk_ids=[str(c.id) for c in db_chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "document_id": str(doc.id),
                    "user_id": str(user_id),
                    "chunk_index": c.chunk_index,
                    "filename": doc.filename,
                }
                for c in db_chunks
            ],
        )

        # 9. Store BM25 tokens (per-user index)
        bm25_index = get_bm25_index(str(user_id))
        bm25_index.upsert_chunks(
            chunk_ids=[str(c.id) for c in db_chunks],
            documents=texts,
            metadatas=[
                {
                    "document_id": str(doc.id),
                    "user_id": str(user_id),
                    "chunk_index": c.chunk_index,
                    "filename": doc.filename,
                }
                for c in db_chunks
            ],
        )

        return DocumentResponse.model_validate(doc)

    async def list_documents(self, user_id: uuid.UUID) -> list[DocumentResponse]:
        docs = await self._doc_repo.list_by_user(user_id)
        return [DocumentResponse.model_validate(d) for d in docs]

    async def delete_document(self, doc_id: uuid.UUID, user_id: uuid.UUID) -> None:
        doc = await self._doc_repo.get(doc_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Remove vectors first (before DB cascades delete chunks)
        self._vector_store.delete_by_document_id(str(doc_id))
        # Remove BM25 tokens
        bm25_index = get_bm25_index(str(user_id))
        bm25_index.delete_by_document_id(str(doc_id))
        await self._doc_repo.delete(doc)
