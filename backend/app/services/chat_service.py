"""
ChatService — orchestrates chat creation, message handling, and workflow invocation.
"""
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

from app.db.models.chat import Chat
from app.db.models.message import Message
from app.repositories.chat_repository import ChatRepository, MessageRepository
from app.schemas.chat import ChatResponse, ChatDetailResponse, MessageResponse
from app.ai.workflow import build_workflow


class ChatService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._chat_repo = ChatRepository(db)
        self._msg_repo = MessageRepository(db)
        self._workflow = build_workflow()

    async def create_chat(self, user_id: uuid.UUID, title: str = "New Chat") -> ChatResponse:
        chat = Chat(user_id=user_id, title=title)
        chat = await self._chat_repo.create(chat)
        return ChatResponse.model_validate(chat)

    async def list_chats(self, user_id: uuid.UUID) -> list[ChatResponse]:
        chats = await self._chat_repo.list_by_user(user_id)
        return [ChatResponse.model_validate(c) for c in chats]

    async def get_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> ChatDetailResponse:
        chat = await self._chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
            
        messages = await self._msg_repo.list_by_chat(chat_id)
        return ChatDetailResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            created_at=chat.created_at,
            messages=[MessageResponse.model_validate(m) for m in messages],
        )

        
    async def delete_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> None:
        chat = await self._chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
        await self._chat_repo.delete(chat)

    async def rename_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID, title: str) -> ChatResponse:
        chat = await self._chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
        chat.title = title
        chat = await self._chat_repo.update(chat)
        return ChatResponse.model_validate(chat)


    async def send_message(self, chat_id: uuid.UUID, user_id: uuid.UUID, content: str):
        # 1. Validate chat ownership
        chat = await self._chat_repo.get(chat_id)
        if not chat or chat.user_id != user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
            
        # 2. Add user message
        user_msg = Message(chat_id=chat_id, role="user", content=content)
        await self._msg_repo.create(user_msg)
        
        # 3. Load conversation history (limit to last 10 messages to preserve token window)
        db_msgs = await self._msg_repo.list_by_chat(chat_id)
        recent_db_msgs = db_msgs[-10:] if len(db_msgs) > 0 else []
        
        langchain_msgs = []
        for m in recent_db_msgs:
            if m.role == "user":
                langchain_msgs.append(HumanMessage(content=m.content))
            else:
                langchain_msgs.append(AIMessage(content=m.content))
                
        # 4. Invoke LangGraph workflow
        state = {
            "messages": langchain_msgs,
            "user_id": str(user_id),
            "query": content
        }
        
        final_state = await self._workflow.ainvoke(state)
        ai_response = final_state.get("response", "Error generating response.")
        
        # Structure citations
        context_chunks = final_state.get("context_chunks", [])
        citations = []
        if context_chunks:
            for chunk in context_chunks:
                meta = chunk.get("metadata", {})
                citations.append({
                    "document_id": meta.get("document_id"),
                    "filename": meta.get("filename"),
                    "chunk_index": meta.get("chunk_index"),
                    "distance": chunk.get("distance")  # for reranking & debug purposes
                })

        # 5. Save AI message
        ai_msg = Message(
            chat_id=chat_id, 
            role="assistant", 
            content=ai_response,
            citations=citations if citations else None
        )
        ai_msg = await self._msg_repo.create(ai_msg)
        
        # Return structured payload payload for immediate UI sync
        return {
            "id": str(ai_msg.id),
            "role": "assistant",
            "content": ai_response,
            "citations": citations,
            "created_at": ai_msg.created_at.isoformat()
        }
