"""Probe Google Places as wired into the agent (orchestrator path).

Runs the same ``fetch_neighborhood_context(listing, icp)`` the render pipeline
uses after ``analyse_photos``. Verifies Geocoding + Nearby + Place Photo +
Hera ``/files`` uploads.

Fast path (default): synthetic ICP dict only — no Vertex / Gemini.

Embedded path (--with-phase1): runs ``run_storyboard_plan`` first so ICP comes
from the real classifier (requires ``GCP_PROJECT`` + ADC).

Run from repo:
    cd backend && .venv/bin/python scripts/probe_places_agent.py
    cd backend && .venv/bin/python scripts/probe_places_agent.py --with-phase1

Or with uv:
    cd backend && uv run python scripts/probe_places_agent.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

DEFAULT_URL = "https://www.airbnb.com/rooms/kreuzberg-loft-demo"


def _load_env() -> None:
    load_dotenv(REPO / ".env")
    creds = REPO / "credentials" / "credentials.env"
    if creds.is_file():
        load_dotenv(creds, override=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe neighborhood_context in agent flow.")
    parser.add_argument(
        "--listing-url",
        default=DEFAULT_URL,
        help="Fixture or scraped listing URL (default: Kreuzberg demo fixture).",
    )
    parser.add_argument(
        "--persona",
        default="Digital nomad",
        help="ICP persona when not using --with-phase1 (default: Digital nomad).",
    )
    parser.add_argument(
        "--with-phase1",
        action="store_true",
        help="Run run_storyboard_plan first so icp comes from classify_icp (needs Vertex).",
    )
    args = parser.parse_args()
    _load_env()

    from src.agent.fixture_loader import load_fixture
    from src.agent.neighborhood_context import fetch_neighborhood_context

    listing = load_fixture(args.listing_url)
    if listing is None:
        print(f"ERROR: no fixture for URL: {args.listing_url}", file=sys.stderr)
        sys.exit(2)

    if args.with_phase1:
        if not os.getenv("GCP_PROJECT"):
            print("ERROR: GCP_PROJECT is not set — cannot run --with-phase1", file=sys.stderr)
            sys.exit(1)
        from src.agent.orchestrator import run_storyboard_plan

        print("Running run_storyboard_plan (Gemini ×3 + visual system)…")
        phase1 = run_storyboard_plan(listing, outpaint_enabled=False)
        icp = phase1.icp or {}
        persona = (icp.get("best_icp") or {}).get("persona") if isinstance(icp, dict) else None
        print(f"Phase1 ICP persona: {persona!r}")
    else:
        icp = {"best_icp": {"persona": args.persona}}
        print(f"Synthetic ICP persona: {args.persona!r}")

    if not (os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")):
        print("ERROR: GOOGLE_PLACES_API_KEY or GOOGLE_MAPS_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not os.getenv("HERA_API_KEY"):
        print("ERROR: HERA_API_KEY not set (needed for /files upload)", file=sys.stderr)
        sys.exit(1)

    print(f"Listing: {listing.title[:60]}… @ {listing.location!r}")
    print("Calling fetch_neighborhood_context (orchestrator-equivalent)…")

    ctx = asyncio.run(fetch_neighborhood_context(listing, icp))

    n = len(ctx.places)
    if n == 0:
        print("RESULT: empty context (Places/Hera failed or no POIs with photos). Check logs.")
        sys.exit(1)

    print(f"RESULT: OK — {n} place(s), {len(ctx.hera_reference_urls)} Hera URL(s)")
    for i, p in enumerate(ctx.places, start=1):
        print(f"  {i}. {p.get('name')} ~{p.get('distance_m')}m rating={p.get('rating')}")
    print("Hera reference URLs (truncated):")
    for u in ctx.hera_reference_urls:
        print(f"  {u[:80]}…" if len(u) > 80 else f"  {u}")

    # Same merge the orchestrator passes into final_assembly
    if ctx.nearby_places_verified:
        sample = ctx.nearby_places_verified[0]
        keys = sorted(sample.keys())
        print(f"nearby_places_verified[0] keys: {keys}")


if __name__ == "__main__":
    main()
