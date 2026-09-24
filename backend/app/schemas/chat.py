"""
Pydantic v2 schemas for chat endpoints.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Any


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: Optional[list] = None
    groundedness: Optional[dict] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ChatDetailResponse(ChatResponse):
    messages: list[MessageResponse] = []


class CreateChatRequest(BaseModel):
    title: str = Field(default="New Chat")


class UpdateChatRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class UserMessageRequest(BaseModel):
    content: str

