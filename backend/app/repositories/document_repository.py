"""Document repository with user-scoped queries."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.document import Document
from app.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Document, db)

    async def list_by_user(self, user_id: UUID) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.user_id == user_id)
        )
        return list(result.scalars().all())
