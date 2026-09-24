"""
Auth router — register, login, refresh, current user profile, and Google OAuth.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.google_auth import (
    create_google_auth_url,
    exchange_code_for_id_token,
    is_google_auth_configured,
    validate_state,
    verify_google_id_token,
)
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.db.models.user import User

router = APIRouter()


def _get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency factory: builds AuthService from the db session."""
    return AuthService(UserRepository(db))


@router.get("/google/status")
async def google_status() -> dict:
    """Report whether Google sign-in is configured. The frontend uses this to
    show/hide the 'Continue with Google' button."""
    return {"configured": is_google_auth_configured()}


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    """Redirect the browser to Google's consent screen."""
    if not is_google_auth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured on the server (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing).",
        )
    return RedirectResponse(url=create_google_auth_url())


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    service: AuthService = Depends(_get_auth_service),
) -> RedirectResponse:
    """
    Google redirects the browser here after consent. Exchange the code for a
    verified identity, log the user in (or create the account), then bounce
    back to the frontend with fresh JWT tokens.
    """
    if not validate_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please try again.",
        )

    try:
        id_tok = exchange_code_for_id_token(code)
        google_info = verify_google_id_token(id_tok)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {exc}",
        )

    tokens = await service.login_or_register_with_google(google_info)

    redirect = (
        f"{settings.FRONTEND_URL}/login"
        f"?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    )
    return RedirectResponse(url=redirect)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Create a new user account and return JWT tokens."""
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Authenticate with email + password, return JWT tokens."""
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)