"""Rate limiting via slowapi.

Per-user keys when authenticated, IP fallback otherwise. Each Hera generate
costs real money + Vertex tokens; slowapi caps protect against signup-spam +
Cost-Spikes on the public Railway URL.

Limits are intentionally lenient — they exist to prevent abuse, not to gate
demo usage.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_or_ip_key(request: Request) -> str:
    """Use Bearer token sub claim when present, else IP. Cheap fallback —
    we don't decode here (auth.py does that on the actual route)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return f"user:{auth_header[7:][:32]}"  # token-prefix; sufficient as bucket key
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_user_or_ip_key,
    default_limits=[],
    # headers_enabled=True needs every rate-limited endpoint to accept a
    # `response: Response` parameter (slowapi injects X-RateLimit-* headers).
    # Without that, slowapi raises a generic 500 that strips the CORS headers,
    # which surfaces as "Failed to fetch" in the browser. The actual rate
    # limiting still works — we just don't expose the remaining-quota headers.
    headers_enabled=False,
)

# Per-route limits are applied as decorators on main.py routes.
LIMIT_LISTING = "10/hour"
LIMIT_GENERATE = "10/hour"
LIMIT_PUBLISH = "6/hour"
LIMIT_METRICS_REFRESH = "12/hour"
