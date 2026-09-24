"""
Google OAuth 2.0 — authorization code flow for "Continue with Google".

FLOW:
  1. Browser hits GET /api/v1/auth/google/login → backend 302-redirects to
     Google's consent screen (with a random `state` stored server-side).
  2. After the user consents, Google redirects the browser back to
     /api/v1/auth/google/callback?code=...&state=...
  3. Backend exchanges the code for an id_token, verifies its signature and
     audience, and (in auth_service) logs the user in or creates an account.

SECURITY:
  - `state` is a one-time random token (stored in memory, 10 min expiry) that
    prevents CSRF on the callback.
  - The id_token is verified against Google's public keys with the exact
    client ID, so only tokens issued for this app are accepted.
"""
import secrets
import time
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE_TTL_SECONDS = 600

# state -> expiry timestamp (in-memory; fine for a single-process app)
_state_store: dict[str, float] = {}


def is_google_auth_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def create_google_auth_url() -> str:
    """Build the Google consent-screen URL for this app."""
    state = secrets.token_urlsafe(32)
    _state_store[state] = time.time() + STATE_TTL_SECONDS
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def validate_state(state: str) -> bool:
    """Consume and validate a state token (single-use, 10 min expiry)."""
    expiry = _state_store.pop(state, None)
    if expiry is None:
        return False
    return time.time() < expiry


def exchange_code_for_id_token(code: str) -> str:
    """Exchange the authorization code for an id_token string."""
    response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    response.raise_for_status()
    token = response.json().get("id_token")
    if not token:
        raise ValueError("Google did not return an id_token")
    return token


def verify_google_id_token(id_token_str: str) -> dict:
    """
    Verify the id_token signature/audience and return its claims.
    Raises google.auth.exceptions.GoogleAuthError on invalid tokens.
    """
    info = id_token.verify_oauth2_token(
        id_token_str,
        google_requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )
    return info