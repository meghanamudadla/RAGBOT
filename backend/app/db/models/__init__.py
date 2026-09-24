# Import all models so Alembic env.py can detect them via metadata
from app.db.models.user import User
from app.db.models.document import Document
from app.db.models.chunk import Chunk
from app.db.models.chat import Chat
from app.db.models.message import Message

__all__ = ["User", "Document", "Chunk", "Chat", "Message"]
