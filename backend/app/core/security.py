"""
Security utilities: password hashing and JWT token creation/validation.

WHY ARGON2:
  Argon2 is the winner of the Password Hashing Competition and is
  recommended over bcrypt. It has tunable memory/time costs that make
  brute-force attacks far more expensive.

WHY SEPARATE ACCESS + REFRESH TOKENS:
  Short-lived access tokens (30 min) reduce the blast radius of a leak.
  Long-lived refresh tokens (7 days) stay server-side verifiable and can
  be revoked (future: store refresh token hash in DB).
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings

# Argon2 via passlib
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    """Internal: create a signed JWT with a type claim."""
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": subject,          # user id (UUID as string)
        "type": token_type,      # "access" | "refresh"
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: UUID) -> str:
    return _create_token(
        subject=str(user_id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(
        subject=str(user_id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str, expected_type: str) -> str:
    """
    Decode and validate a JWT.
    Returns the user_id (subject) on success.
    Raises ValueError on any failure so callers get a clean exception.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            raise ValueError("Invalid token type")
        sub: str | None = payload.get("sub")
        if sub is None:
            raise ValueError("Token missing subject")
        return sub
    except JWTError as exc:
        raise ValueError(f"Token invalid or expired: {exc}") from exc
