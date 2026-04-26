"""Scrape one Airbnb URL with Playwright and dump the result as a fixture JSON.

Usage:
    uv run python backend/scripts/scrape_to_fixture.py <URL> <FIXTURE_NAME>

Run from a residential IP — Airbnb walls Railway/datacenter IPs. The output
goes into backend/src/agent/fixtures/<FIXTURE_NAME>.json and you must then
register the listing's room ID in fixture_loader.FIXTURES_BY_ROOM_ID.

Reuses _scrape_via_playwright so this stays in lockstep with prod scraping.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from src.agent.scraper import _scrape_via_playwright

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "src" / "agent" / "fixtures"


async def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    url, fixture_name = sys.argv[1], sys.argv[2]
    if not fixture_name.endswith(".json"):
        fixture_name += ".json"

    print(f"scrape_to_fixture: starting url={url}")
    listing = await _scrape_via_playwright(url)
    if listing is None:
        print("scrape_to_fixture: scraper returned None — see logs above")
        return 1

    out_path = _FIXTURES_DIR / fixture_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(listing.model_dump(), ensure_ascii=False, indent=2))
    print(
        f"scrape_to_fixture: wrote {out_path} "
        f"(title={listing.title[:60]!r}, photos={len(listing.photos)}, "
        f"review_quotes={len(listing.review_quotes)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
