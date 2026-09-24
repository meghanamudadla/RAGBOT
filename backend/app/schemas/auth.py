"""
Pydantic v2 schemas for authentication endpoints.

WHY SEPARATE REQUEST/RESPONSE SCHEMAS:
  Request schemas validate incoming data (e.g., enforce email format,
  min password length) before it ever touches the DB.
  Response schemas control what fields are returned — we never expose
  hashed_password or internal IDs unintentionally.
"""
from pydantic import BaseModel, EmailStr, Field
import uuid


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool

    model_config = {"from_attributes": True}  # allows conversion from ORM objects
