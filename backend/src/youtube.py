"""YouTube Data API v3 wrapper — OAuth flow + resumable upload + statistics.

Uses a SEPARATE OAuth client (GOOGLE_OAUTH_CLIENT_ID_YOUTUBE / SECRET) decoupled
from the Supabase Google sign-in client and from the Vertex/ADC service account.
This is intentional: sign-in needs `openid email profile`; YouTube auto-deploy
needs `youtube.upload + youtube.readonly`. Same Google account, different consent
screen.

Tokens are stored per-user in `user_youtube_tokens`. Refresh happens lazily
when the access_token is within 60s of expiry — googleapiclient handles the
actual refresh via `Credentials.refresh()` and we persist the new token back.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.logger import log
from src.supabase_client import get_supabase_client

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
_TOKEN_TABLE = "user_youtube_tokens"
_STATE_TTL_SECONDS = 600  # 10 min — covers slow OAuth consent flows


def _client_config() -> dict[str, Any]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID_YOUTUBE", "")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_YOUTUBE", "")
    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_ID_YOUTUBE / SECRET not configured")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _redirect_uri() -> str:
    base = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/api/youtube/callback"


def _state_signer() -> URLSafeTimedSerializer:
    # Reuse the JWT secret as state-signing key — it's already required for auth
    # and never leaves the server.
    secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("HERA_API_KEY") or "dev-state-secret"
    return URLSafeTimedSerializer(secret, salt="youtube-oauth-state")


def build_consent_url(user_id: str) -> str:
    """Build the Google consent URL for a given user. State carries user_id
    signed + timed so the callback can match the exchange to the right user
    without an in-memory session."""
    flow = Flow.from_client_config(_client_config(), scopes=YOUTUBE_SCOPES)
    flow.redirect_uri = _redirect_uri()
    state = _state_signer().dumps({"user_id": user_id})
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # always show consent so refresh_token is issued
        state=state,
    )
    return auth_url


def verify_state(state: str) -> str:
    """Returns user_id; raises ValueError if state is bad/expired."""
    try:
        data = _state_signer().loads(state, max_age=_STATE_TTL_SECONDS)
    except BadSignature as exc:
        raise ValueError("invalid_state") from exc
    if not isinstance(data, dict) or "user_id" not in data:
        raise ValueError("invalid_state_payload")
    return str(data["user_id"])


def exchange_code(code: str) -> Credentials:
    flow = Flow.from_client_config(_client_config(), scopes=YOUTUBE_SCOPES)
    flow.redirect_uri = _redirect_uri()
    flow.fetch_token(code=code)
    return flow.credentials


def _persist_tokens(
    user_id: str,
    creds: Credentials,
    channel_id: str | None,
    channel_title: str | None,
) -> None:
    supabase = get_supabase_client()
    if supabase is None:
        log.warning("youtube: supabase unavailable, cannot persist tokens for user=%s", user_id)
        return
    expires_at = creds.expiry.replace(tzinfo=UTC) if creds.expiry else (
        datetime.now(UTC) + timedelta(hours=1)
    )
    row = {
        "user_id": user_id,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token or "",
        "expires_at": expires_at.isoformat(),
        "scopes": list(creds.scopes or YOUTUBE_SCOPES),
        "channel_id": channel_id,
        "channel_title": channel_title,
    }
    supabase.table(_TOKEN_TABLE).upsert(row).execute()
    log.info(
        "youtube: persisted tokens user=%s channel=%r expires_at=%s",
        user_id,
        channel_title,
        expires_at.isoformat(),
    )


def _load_tokens(user_id: str) -> dict[str, Any] | None:
    supabase = get_supabase_client()
    if supabase is None:
        return None
    res = supabase.table(_TOKEN_TABLE).select("*").eq("user_id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def _credentials_from_row(row: dict[str, Any]) -> Credentials:
    return Credentials(
        token=row["access_token"],
        refresh_token=row.get("refresh_token") or None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID_YOUTUBE"),
        client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_YOUTUBE"),
        scopes=row.get("scopes") or YOUTUBE_SCOPES,
    )


def get_credentials(user_id: str) -> Credentials | None:
    row = _load_tokens(user_id)
    if not row:
        return None
    creds = _credentials_from_row(row)
    if not creds.valid and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            _persist_tokens(user_id, creds, row.get("channel_id"), row.get("channel_title"))
        except Exception as exc:  # noqa: BLE001 — best-effort refresh
            log.error("youtube: refresh failed user=%s err=%s", user_id, exc)
            return None
    return creds


def fetch_my_channel(creds: Credentials) -> dict[str, Any] | None:
    """Returns the user's first owned channel (id + snippet.title) or None.
    None means the Google account has no YouTube channel — the OAuth callback
    treats this as a soft error and prompts the user to create one."""
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    resp = yt.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items") or []
    if not items:
        return None
    item = items[0]
    return {
        "id": item.get("id"),
        "title": (item.get("snippet") or {}).get("title"),
    }


def complete_oauth(user_id: str, code: str) -> dict[str, Any]:
    """Full callback: exchange code, fetch channel, persist tokens.
    Returns {connected: bool, channel_title: str|None, error: str|None}."""
    creds = exchange_code(code)
    channel = fetch_my_channel(creds)
    channel_id = channel["id"] if channel else None
    channel_title = channel["title"] if channel else None
    _persist_tokens(user_id, creds, channel_id, channel_title)
    if channel is None:
        return {"connected": False, "channel_title": None, "error": "no_channel"}
    return {"connected": True, "channel_title": channel_title, "error": None}


def get_status(user_id: str) -> dict[str, Any]:
    row = _load_tokens(user_id)
    if not row:
        return {"connected": False}
    expires_at_raw = row.get("expires_at")
    expires_soon = False
    if isinstance(expires_at_raw, str):
        try:
            expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
            expires_soon = expires_at - datetime.now(UTC) < timedelta(minutes=5)
        except ValueError:
            pass
    return {
        "connected": True,
        "channel_id": row.get("channel_id"),
        "channel_title": row.get("channel_title"),
        "expires_soon": expires_soon,
    }


def disconnect(user_id: str) -> None:
    supabase = get_supabase_client()
    if supabase is None:
        return
    supabase.table(_TOKEN_TABLE).delete().eq("user_id", user_id).execute()


def upload_video(
    user_id: str,
    video_bytes: bytes,
    title: str,
    description: str,
    visibility: str = "unlisted",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Upload an MP4 to the user's YouTube channel and return YouTube metadata.

    Resumable upload via MediaIoBaseUpload — no tempfile, the bytes live in
    memory. Hera-rendered Shorts are ~3-10 MB so this is comfortable.
    """
    creds = get_credentials(user_id)
    if creds is None:
        raise RuntimeError("YouTube not connected for this user")
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or [],
            "categoryId": "19",  # Travel & Events
        },
        "status": {
            "privacyStatus": visibility,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaIoBaseUpload(BytesIO(video_bytes), mimetype="video/mp4", resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _status, response = request.next_chunk()
    log.info(
        "youtube: uploaded video user=%s id=%s title=%r visibility=%s",
        user_id,
        response.get("id"),
        title[:60],
        visibility,
    )
    return {
        "video_id": response.get("id"),
        "channel_id": (response.get("snippet") or {}).get("channelId"),
        "published_at": (response.get("snippet") or {}).get("publishedAt"),
    }


def fetch_statistics(user_id: str, youtube_video_id: str) -> dict[str, Any]:
    creds = get_credentials(user_id)
    if creds is None:
        raise RuntimeError("YouTube not connected for this user")
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    resp = yt.videos().list(part="statistics", id=youtube_video_id).execute()
    items = resp.get("items") or []
    if not items:
        return {}
    stats = items[0].get("statistics") or {}
    return {
        "view_count": int(stats.get("viewCount", 0) or 0),
        "like_count": int(stats.get("likeCount", 0) or 0),
        "comment_count": int(stats.get("commentCount", 0) or 0),
    }
