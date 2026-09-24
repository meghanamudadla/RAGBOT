"""
Chat router — endpoints for managing conversational sessions and message sending.
Replaces the placeholder router.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.db.models.user import User
from app.services.chat_service import ChatService
from app.schemas.chat import (
    CreateChatRequest, 
    UpdateChatRequest,
    ChatResponse, 
    ChatDetailResponse,
    UserMessageRequest
)

router = APIRouter()

def _get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    """Dependency factory: builds ChatService from the db session."""
    return ChatService(db)

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: CreateChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> ChatResponse:
    """Initialize a new empty chat session."""
    return await service.create_chat(current_user.id, payload.title)

@router.get("/", response_model=list[ChatResponse])
async def list_chats(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> list[ChatResponse]:
    """List all prior chat histories ordered chronologically descending."""
    return await service.list_chats(current_user.id)

@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(
    chat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> ChatDetailResponse:
    """Retrieve chat session details and message history."""
    return await service.get_chat(chat_id, current_user.id)

@router.patch("/{chat_id}", response_model=ChatResponse)
async def rename_chat(
    chat_id: uuid.UUID,
    payload: UpdateChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> ChatResponse:
    """Rename a chat session."""
    return await service.rename_chat(chat_id, current_user.id, payload.title)

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> None:
    """Delete a chat and its cascade-deleted messages entirely."""
    await service.delete_chat(chat_id, current_user.id)


@router.post("/{chat_id}/message")
async def send_message(
    chat_id: uuid.UUID,
    payload: UserMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    """Synchronous (non-streaming) message endpoint. Returns full response at once."""
    return await service.send_message(chat_id, current_user.id, payload.content)


@router.post("/{chat_id}/stream")
async def stream_message(
    chat_id: uuid.UUID,
    payload: UserMessageRequest,
    current_user: User = Depends(get_current_user),
):
    """
    SSE streaming endpoint.
    Returns a text/event-stream where each event is:
      data: {"token": "<text>"}\n\n   — partial LLM output
      data: {"done": true, "citations": [...], "message_id": "..."}\n\n  — final event
    """
    from fastapi.responses import StreamingResponse
    from app.ai.streaming import stream_rag_response

    return StreamingResponse(
        stream_rag_response(chat_id, current_user.id, payload.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
