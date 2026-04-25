"""Load synthetic listing fixtures by URL slug.

v1 ships with one fixture. Add entries to FIXTURES to support more slugs.
"""

import json
from pathlib import Path

from src.agent.models import ScrapedListing

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Map URL slug (end of URL) → fixture filename
FIXTURES: dict[str, str] = {
    "kreuzberg-loft-demo": "kreuzberg-loft.json",
}


def load_fixture(listing_url: str) -> ScrapedListing | None:
    """Return a ScrapedListing if listing_url ends with a known fixture slug, else None."""
    for slug, filename in FIXTURES.items():
        if listing_url.rstrip("/").endswith(slug):
            path = _FIXTURES_DIR / filename
            data = json.loads(path.read_text(encoding="utf-8"))
            return ScrapedListing(**data)
    return None
