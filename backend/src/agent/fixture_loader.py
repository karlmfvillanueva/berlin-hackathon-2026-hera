"""Load pre-scraped listing fixtures.

Two match strategies:
  1. **Room ID** — extracted from `/rooms/{id}` in the URL (Airbnb's stable
     identifier; query strings vary across sessions but the ID does not).
  2. **Trailing slug** — legacy support for the seed `kreuzberg-loft-demo`
     URL that doesn't follow the `/rooms/{id}` shape.

Pre-scraped fixtures are how the demo flow stays bulletproof: judges land on
URLs we control, the scraper never needs to leave Railway's IP, no Airbnb
anti-bot lottery. Add new fixtures by running
`backend/scripts/scrape_to_fixture.py <url> <name>` from a residential IP,
then registering the resulting room ID below.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.agent.models import ScrapedListing

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Map Airbnb room ID → fixture filename. The room ID is the digits in
# /rooms/{id}; query strings are stripped by the regex match.
FIXTURES_BY_ROOM_ID: dict[str, str] = {
    "648914239689489448": "property-1.json",
    "1135417764953008513": "property-2.json",
    "1175975083652953434": "property-3.json",
}

# Legacy slug fixtures — URL ends with this string. Kept for the seed
# kreuzberg-loft-demo URL that pre-dates the room-ID matching.
FIXTURES_BY_SLUG: dict[str, str] = {
    "kreuzberg-loft-demo": "kreuzberg-loft.json",
}

_ROOM_ID_RE = re.compile(r"/rooms/(\d+)")


def load_fixture(listing_url: str) -> ScrapedListing | None:
    """Return a ScrapedListing if the URL matches a known fixture, else None."""
    match = _ROOM_ID_RE.search(listing_url)
    if match:
        room_id = match.group(1)
        filename = FIXTURES_BY_ROOM_ID.get(room_id)
        if filename:
            return _load(filename)

    cleaned = listing_url.rstrip("/")
    for slug, filename in FIXTURES_BY_SLUG.items():
        if cleaned.endswith(slug):
            return _load(filename)

    return None


def fixture_room_ids() -> list[str]:
    """All room IDs we have a fixture for. Used by the API to expose which
    listings the demo-mode UI should surface as picker cards."""
    return list(FIXTURES_BY_ROOM_ID.keys())


def _load(filename: str) -> ScrapedListing:
    path = _FIXTURES_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    return ScrapedListing(**data)
