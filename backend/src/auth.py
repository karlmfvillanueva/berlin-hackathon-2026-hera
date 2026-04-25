"""Supabase JWT authentication for FastAPI routes.

Validates Supabase-issued JWTs (HS256, audience='authenticated') and exposes
`current_user` as a FastAPI dependency.

Dev bypass: when `REQUIRE_AUTH=false`, `current_user` returns a synthetic dev
user without inspecting the Authorization header. This keeps `make dev` working
while the frontend auth wiring is still in flight, and is safe because Railway
production runs with `REQUIRE_AUTH=true`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.logger import log

_DEV_BYPASS_USER_ID = "00000000-0000-0000-0000-000000000000"
_DEV_BYPASS_EMAIL = "dev@local"


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None


def _require_auth_enabled() -> bool:
    return os.getenv("REQUIRE_AUTH", "true").lower() != "false"


# auto_error=False: when REQUIRE_AUTH=false, requests without Authorization header
# must NOT 403 — we hand them through as the dev-bypass user.
_bearer_scheme = HTTPBearer(auto_error=False)


def _decode_supabase_jwt(token: str) -> dict:
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        log.error("auth: SUPABASE_JWT_SECRET is not set; cannot validate tokens")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "auth_not_configured"},
        )
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_expired"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


_BearerCreds = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


def current_user(creds: _BearerCreds) -> AuthenticatedUser:
    """FastAPI dep — validates Supabase JWT or returns dev-bypass user."""
    if not _require_auth_enabled():
        return AuthenticatedUser(user_id=_DEV_BYPASS_USER_ID, email=_DEV_BYPASS_EMAIL)

    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing_bearer_token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_supabase_jwt(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token_claims"},
        )
    return AuthenticatedUser(user_id=sub, email=payload.get("email"))


def optional_user(creds: _BearerCreds) -> AuthenticatedUser | None:
    """Like current_user, but returns None instead of 401 when no token is present.

    Used by routes that behave differently for logged-in vs anonymous users
    (e.g. dashboard with optional demo-seed inclusion) without forcing 401.
    """
    if not _require_auth_enabled():
        return AuthenticatedUser(user_id=_DEV_BYPASS_USER_ID, email=_DEV_BYPASS_EMAIL)
    if creds is None or not creds.credentials:
        return None
    try:
        # current_user takes the same creds parameter; pass through.
        return current_user(creds)  # type: ignore[arg-type]
    except HTTPException:
        return None
