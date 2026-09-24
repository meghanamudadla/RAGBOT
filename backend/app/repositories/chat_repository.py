"""Chat and Message repositories."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.chat import Chat
from app.db.models.message import Message
from app.repositories.base_repository import BaseRepository


class ChatRepository(BaseRepository[Chat]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Chat, db)

    async def list_by_user(self, user_id: UUID) -> list[Chat]:
        result = await self.db.execute(
            select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at.desc())
        )
        return list(result.scalars().all())


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Message, db)

    async def list_by_chat(self, chat_id: UUID) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
