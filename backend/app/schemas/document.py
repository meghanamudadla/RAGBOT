"""
Pydantic v2 schemas for document endpoints.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    uploaded_at: datetime
    user_id: uuid.UUID

    model_config = {"from_attributes": True}
