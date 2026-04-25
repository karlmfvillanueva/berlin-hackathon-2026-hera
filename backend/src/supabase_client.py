"""Lazy Supabase service-role client.

Returns None when SUPABASE_URL or SUPABASE_SERVICE_KEY is unset so the rest of the
backend can run in stateless mode (Phase 1 behaviour). Phase 2 features that need
persistence — `videos` row insert, `agent_beliefs` fetch — must check for None.
"""

import os
from functools import lru_cache

from supabase import Client, create_client

from src.logger import log


@lru_cache(maxsize=1)
def get_supabase_client() -> Client | None:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not url or not key:
        log.warning(
            "supabase: SUPABASE_URL or SUPABASE_SERVICE_KEY missing — running stateless"
        )
        return None
    log.info("supabase: client initialised url=%s", url)
    return create_client(url, key)
