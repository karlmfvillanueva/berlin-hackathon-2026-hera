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
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.logger import log

_DEV_BYPASS_USER_ID = "00000000-0000-0000-0000-000000000000"
_DEV_BYPASS_EMAIL = "dev@local"

# Supabase moved to asymmetric JWT signing keys (ECDSA / ES256) in late 2024.
# New-style projects sign with a private key and publish the public key at the
# project's JWKS endpoint; legacy projects still use HS256 + a shared secret.
# We support both: peek at the token's `alg` and pick the right verification path.


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None


def _require_auth_enabled() -> bool:
    return os.getenv("REQUIRE_AUTH", "true").lower() != "false"


# auto_error=False: when REQUIRE_AUTH=false, requests without Authorization header
# must NOT 403 — we hand them through as the dev-bypass user.
_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient | None:
    """PyJWKClient that fetches Supabase's signing keys from the project's
    JWKS endpoint. Cached for the lifetime of the process; PyJWKClient itself
    caches keys with TTL so a key rotation is picked up without a restart."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        return None
    return jwt.PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")


def _decode_supabase_jwt(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    alg = header.get("alg", "HS256")

    try:
        if alg == "HS256":
            secret = os.getenv("SUPABASE_JWT_SECRET")
            if not secret:
                log.error("auth: SUPABASE_JWT_SECRET is not set; cannot validate HS256 tokens")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"error": "auth_not_configured"},
                )
            return jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

        client = _jwks_client()
        if client is None:
            log.error("auth: SUPABASE_URL is not set; cannot resolve JWKS for alg=%s", alg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "auth_not_configured"},
            )
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
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
    """FastAPI dep — validates Supabase JWT or returns dev-bypass user.

    Dev mode (REQUIRE_AUTH=false) still prefers a real JWT when the frontend
    sends one. Without this, locally-logged-in devs got stamped with the nil
    user_id and inserts into `videos` failed the FK to auth.users, surfacing
    as 'Saving to your library failed' on the done screen.
    """
    has_token = (
        creds is not None
        and creds.scheme.lower() == "bearer"
        and bool(creds.credentials)
    )

    if not _require_auth_enabled():
        if has_token:
            try:
                payload = _decode_supabase_jwt(creds.credentials)
                sub = payload.get("sub")
                if sub:
                    return AuthenticatedUser(user_id=sub, email=payload.get("email"))
            except HTTPException:
                # Bad/expired token in dev — fall through to bypass rather than 401.
                pass
        return AuthenticatedUser(user_id=_DEV_BYPASS_USER_ID, email=_DEV_BYPASS_EMAIL)

    if not has_token:
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
    if creds is None or not creds.credentials:
        if not _require_auth_enabled():
            return AuthenticatedUser(user_id=_DEV_BYPASS_USER_ID, email=_DEV_BYPASS_EMAIL)
        return None
    try:
        # current_user takes the same creds parameter; pass through.
        return current_user(creds)  # type: ignore[arg-type]
    except HTTPException:
        return None
