"""
FastAPI dependency for extracting and validating the current authenticated user.

WHY A DEDICATED DEPENDENCY:
  FastAPI dependencies compose cleanly. Any route can declare
  `current_user: User = Depends(get_current_user)` and the framework
  handles everything — extraction, validation, error response — without
  repeating code in every handler.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_token
from app.repositories.user_repository import UserRepository
from app.db.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract Bearer token, decode it, and return the active User."""
    try:
        user_id = decode_token(credentials.credentials, expected_type="access")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    from uuid import UUID
    repo = UserRepository(db)
    user = await repo.get(UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
        )
    return user
