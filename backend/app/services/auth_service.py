"""
AuthService — business logic for registration, login, token refresh,
and Google OAuth sign-in.

WHY SERVICE LAYER:
  The router should only handle HTTP concerns (parse request, return response).
  Business logic lives here so it can be unit-tested without HTTP overhead.
"""
import secrets

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.repositories.user_repository import UserRepository
from app.db.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from fastapi import HTTPException, status


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        # 1. Check email uniqueness
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # 2. Create user
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
        )
        user = await self.user_repo.create(user)

        # 3. Return tokens
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(payload.email)

        # Validate credentials — use constant-time verify even on None to prevent
        # timing-based user enumeration attacks
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def login_or_register_with_google(self, google_info: dict) -> TokenResponse:
        """
        Find-or-create a user from verified Google claims.

        Users created via Google get an unguessable random password hash that
        can never be used for password login (they authenticate via Google).
        """
        email = (google_info.get("email") or "").lower()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account has no email address",
            )
        if not google_info.get("email_verified"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google email is not verified",
            )

        user = await self.user_repo.get_by_email(email)
        if not user:
            user = User(
                email=email,
                hashed_password=f"!google-oauth:{secrets.token_urlsafe(32)}",
            )
            user = await self.user_repo.create(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        # Validate refresh token
        try:
            user_id = decode_token(refresh_token, expected_type="refresh")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )

        # Ensure user still exists and is active
        from uuid import UUID
        user = await self.user_repo.get(UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def get_current_user(self, user_id: str) -> User:
        """Helper used by the auth dependency."""
        from uuid import UUID
        user = await self.user_repo.get(UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user