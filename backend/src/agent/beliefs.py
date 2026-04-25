"""Fetch the agent's currently-held editorial beliefs from Supabase.

Phase 2 wiring: the orchestrator pulls the top-N beliefs by confidence and the
classifier injects them into its system prompt as a "Your beliefs" block.

When Supabase is not configured (or the query fails), this returns an empty list
and the classifier runs with the Phase-1 system prompt — graceful degradation.
"""

from src.agent.models import Belief
from src.logger import log
from src.supabase_client import get_supabase_client


def fetch_beliefs(limit: int = 10) -> list[Belief]:
    client = get_supabase_client()
    if client is None:
        return []
    try:
        res = (
            client.table("agent_beliefs")
            .select("rule_key,rule_text,confidence")
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        return [Belief(**row) for row in res.data]
    except Exception as exc:
        log.warning("beliefs: fetch failed — falling back to empty list. err=%s", exc)
        return []
