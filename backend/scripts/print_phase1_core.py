"""Print the four core Phase-1 agent blobs (ICP, location, reviews, visual).

Run from repo root (with backend deps and PYTHONPATH)::

    cd backend
    export PYTHONPATH="$PWD"
    export REQUIRE_AUTH=false
    python scripts/print_phase1_core.py
    python scripts/print_phase1_core.py https://www.airbnb.com/rooms/some-id

or with ``uv``::

    cd backend && uv run python scripts/print_phase1_core.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
for path in (
    _REPO_ROOT / "credentials" / "credentials.env",
    _REPO_ROOT / ".env",
):
    if path.is_file():
        load_dotenv(path)
load_dotenv()

# Ensure `src` package resolves when run as ``python scripts/...``.
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.agent import run_storyboard_plan  # noqa: E402
from src.agent.fixture_loader import load_fixture  # noqa: E402

DEFAULT_URL = "https://www.airbnb.com/rooms/kreuzberg-loft-demo"
KEYS = ("icp", "location_enrichment", "reviews_evaluation", "visual_system")


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    listing = load_fixture(url)
    if listing is None:
        print(f"No fixture for URL: {url}", file=sys.stderr)
        sys.exit(1)
    phase1 = run_storyboard_plan(listing, outpaint_enabled=False)
    data = phase1.model_dump()
    for key in KEYS:
        print(f"=== {key} ===")
        print(json.dumps(data.get(key), indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()
