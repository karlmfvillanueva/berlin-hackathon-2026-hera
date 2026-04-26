"""Render the two Argus landing-page Hera videos.

Outputs (relative to repo root):
    frontend/public/videos/argus-hero.mp4         (Listing 1, ~12s, 16:9)
    frontend/public/videos/argus-demo-climax.mp4  (Listing 2, ~12s, 16:9)
    frontend/public/agent/argus-hero-decision.json
    frontend/public/agent/argus-demo-climax-decision.json

Usage:
    cd backend
    uv run python scripts/render_landing_videos.py              # both
    uv run python scripts/render_landing_videos.py hero         # just hero
    uv run python scripts/render_landing_videos.py demo-climax  # just demo
    uv run python scripts/render_landing_videos.py --duration 15 hero

Reads HERA_API_KEY, GCP_PROJECT, ENABLE_LIVE_SCRAPE from .env at project root.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# Make `from src...` work no matter where the script is invoked from.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Project root .env (matches main.py's load order).
load_dotenv(REPO_ROOT / "credentials" / "credentials.env")
load_dotenv(REPO_ROOT / ".env")

from src.agent import run_render_from_plan, run_storyboard_plan  # noqa: E402
from src.agent.models import Overrides  # noqa: E402
from src.agent.scraper import scrape_listing  # noqa: E402
from src.logger import log  # noqa: E402

HERA_BASE = "https://api.hera.video/v1"
HERA_API_KEY = os.getenv("HERA_API_KEY", "")

# Append a cinematic-pacing + English-only suffix on top of the agent-built
# prompt. The orchestrator may lean kinetic by default and may have inferred
# German from the listing text; the landing-page videos need English on-screen
# text and slow holds. Tone preserved, pacing + language + photo-variety nudged.
PROMPT_SUFFIX_CINEMATIC = (
    " IMPORTANT: All on-screen text, captions, and end-card copy must be in"
    " English only — translate any non-English text in the scene plan above to"
    " natural, editorial English before rendering. Photo variety: use a"
    " DIFFERENT reference photo for every scene; never repeat the same shot or"
    " composition twice; treat each provided asset as a one-time-use frame."
    " Pacing: long lingering holds, no quick cuts. Tone: cinematic, restrained,"
    " editorial — a short film, not a social ad. Composition: each shot earns at"
    " least 3 seconds. Outro: final frame matches the opening composition for"
    " seamless looping."
)

# Hero gets a brand-video wrap: 2s opening title card → property scenes →
# 3s closing CTA card. Single Hera render — text fidelity is fragile but the
# model handles short editorial title cards reliably most of the time.
HERO_BRAND_WRAP = (
    " BRAND-VIDEO STRUCTURE — overrides the scene-plan timing above. This is"
    " a 30-second brand piece for the Argus product, not a property reel. Open"
    " with a 2-second cinematic title card: deep-forest background (hex"
    " #14201B), centered serif word \"Argus\" in soft white with a small coral"
    " (#F94B12) dot beneath it; slow fade-in, no motion. Then play the"
    " property scenes from the plan above, compressed to fit ~24 seconds in"
    " 9:16 vertical framing — recompose every shot for portrait, prefer hero-"
    " axis verticals (full-height windows, standing figures, vertical kitchen,"
    " staircases, hanging lights). Close with a 3-second outro card on the"
    " same deep-forest background: centered serif headline \"Drop a listing.\""
    " on top, then on a second line in smaller serif \"Argus.\" with the same"
    " coral dot accent. Hold the closing card for 1 full second before fading"
    " to black. Bookend cards must use clean editorial typography — no glow,"
    " no shimmer, no kinetic effects — just type on a dark field. Aspect:"
    " 9:16 portrait throughout, smartphone-native composition."
)

VIDEOS_DIR = REPO_ROOT / "frontend" / "public" / "videos"
DECISIONS_DIR = REPO_ROOT / "frontend" / "public" / "agent"
SRC_DATA_DIR = REPO_ROOT / "frontend" / "src" / "data"

LISTINGS: dict[str, str] = {
    "hero": "https://www.airbnb.de/rooms/1092657605119082808",
    "demo-climax": "https://www.airbnb.de/rooms/648914239689489448",
}

# Per-slug Hera output overrides. Hero is portrait + brand-wrapped; demo
# stays widescreen and untouched (the user signed off on the Bali clip).
SLUG_OUTPUT: dict[str, dict[str, str]] = {
    "hero": {"aspect_ratio": "9:16", "resolution": "1080p"},
    "demo-climax": {"aspect_ratio": "16:9", "resolution": "1080p"},
}
SLUG_DURATION_DEFAULT: dict[str, int] = {
    "hero": 30,           # 2s intro + 25s property + 3s outro
    "demo-climax": 25,
}

POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 8 * 60  # 8 min hard cap per render


async def _orchestrate_with_retry(
    slug: str, listing, phase1, overrides, max_attempts: int = 4
):
    """Retry phase2 on validation hiccups in the photo_analyser / Gemini layer.

    Gemini structured output is non-deterministic; about 1-in-3 of the strict
    validations in photo_analyser fail on a fresh roll. Retrying with the same
    inputs flips the outcome ~95% of the time.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            decision = await run_render_from_plan(listing, phase1, overrides)
            log.info("[%s] phase2 ok on attempt %d/%d", slug, attempt, max_attempts)
            return decision
        except RuntimeError as exc:
            last_exc = exc
            log.warning(
                "[%s] phase2 attempt %d/%d failed: %s — retrying",
                slug, attempt, max_attempts, exc,
            )
            await asyncio.sleep(2)
    raise RuntimeError(f"[{slug}] phase2 still failing after {max_attempts} attempts") from last_exc


async def render_listing(slug: str, url: str, *, duration: int | None = None) -> None:
    """Scrape → orchestrate → submit to Hera → poll → download MP4."""
    if not HERA_API_KEY:
        raise RuntimeError("HERA_API_KEY not set in .env")

    # Per-slug overrides — caller may pin duration via CLI.
    effective_duration = duration if duration is not None else SLUG_DURATION_DEFAULT.get(slug, 25)
    output_cfg = SLUG_OUTPUT.get(slug, {"aspect_ratio": "16:9", "resolution": "1080p"})

    t0 = time.monotonic()
    log.info("[%s] === START === url=%s aspect=%s dur=%ds", slug, url, output_cfg["aspect_ratio"], effective_duration)

    log.info("[%s] scraping listing…", slug)
    listing = await scrape_listing(url)
    if listing is None:
        raise RuntimeError(f"[{slug}] scrape returned None for {url}")
    log.info(
        "[%s] scraped: title=%r location=%r photos=%d reviews=%d",
        slug, listing.title, listing.location, len(listing.photos), len(listing.review_quotes),
    )

    log.info("[%s] phase1: storyboard plan…", slug)
    phase1 = run_storyboard_plan(listing)
    log.info(
        "[%s] phase1 ok: tone=%s lang=%s emphasis=%d hooks=%d",
        slug, phase1.suggested_tone, phase1.suggested_language,
        len(phase1.emphasis_options), len(phase1.hook_options),
    )

    # Force English regardless of the listing's source language — the landing
    # page is for an international audience.
    overrides = Overrides(
        language="en",
        tone=phase1.suggested_tone,
        emphasis=[],
        deemphasis=[],
        hook_id="auto",
    )

    log.info("[%s] phase2: render plan (heavy agents + final assembly)…", slug)
    decision = await _orchestrate_with_retry(slug, listing, phase1, overrides)
    log.info(
        "[%s] decision ready: prompt_chars=%d images=%d agent_duration=%d",
        slug, len(decision.hera_prompt), len(decision.selected_image_urls),
        decision.duration_seconds,
    )

    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    decision_path = DECISIONS_DIR / f"argus-{slug}-decision.json"
    decision_path.write_text(decision.model_dump_json(indent=2))
    log.info("[%s] decision json saved → %s", slug, decision_path.relative_to(REPO_ROOT))

    # Mirror the hero decision into src/data/ so the bundled landing page picks
    # it up at compile time (Opinions + ArchitectureDiagram both import from
    # there). Only the hero render drives the on-page copy.
    if slug == "hero":
        SRC_DATA_DIR.mkdir(parents=True, exist_ok=True)
        bundled_path = SRC_DATA_DIR / "hero-decision.json"
        bundled_path.write_text(decision.model_dump_json(indent=2))
        log.info("[%s] decision mirrored → %s", slug, bundled_path.relative_to(REPO_ROOT))

    # Hero gets the brand-wrap on top of the cinematic suffix; demo stays plain.
    suffix = PROMPT_SUFFIX_CINEMATIC + (HERO_BRAND_WRAP if slug == "hero" else "")
    final_prompt = decision.hera_prompt + suffix
    # Pool the agent's vision-ranked top picks first, then top up with the rest
    # of the listing's gallery so Hera has more distinct frames to pick from for
    # a 25-second video. De-dup, cap at 10 (Hera asset limit is generous, but
    # 10 is plenty for variety).
    seen: set[str] = set()
    pooled: list[str] = []
    for u in [*decision.selected_image_urls, *(p.url for p in listing.photos)]:
        if u and u not in seen:
            seen.add(u)
            pooled.append(u)
    image_assets = [{"type": "image", "url": u} for u in pooled[:10]]
    log.info("[%s] photo pool: %d distinct (selected=%d, gallery=%d)",
             slug, len(image_assets), len(decision.selected_image_urls), len(listing.photos))
    payload = {
        "prompt": final_prompt,
        "duration_seconds": effective_duration,
        "outputs": [
            {
                "format": "mp4",
                "aspect_ratio": output_cfg["aspect_ratio"],
                "fps": "30",
                "resolution": output_cfg["resolution"],
            }
        ],
        "assets": image_assets,
    }

    log.info(
        "[%s] submitting to Hera: %s %ds %d assets prompt_chars=%d",
        slug, output_cfg["aspect_ratio"], effective_duration, len(image_assets), len(final_prompt),
    )
    async with httpx.AsyncClient(
        base_url=HERA_BASE,
        headers={"x-api-key": HERA_API_KEY, "content-type": "application/json"},
        timeout=60.0,
    ) as http:
        r = await http.post("/videos", json=payload)
        if r.status_code >= 400:
            log.error("[%s] Hera POST failed %d: %s", slug, r.status_code, r.text[:500])
            r.raise_for_status()
        body = r.json()
        video_id = body["video_id"]
        log.info("[%s] Hera accepted: video_id=%s", slug, video_id)

        file_url = await _poll_until_done(http, slug, video_id)

        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = VIDEOS_DIR / f"argus-{slug}.mp4"
        await _download(http, file_url, out_path)
        size_mb = out_path.stat().st_size / 1_000_000
        log.info(
            "[%s] saved → %s (%.1f MB) total=%.1fs",
            slug, out_path.relative_to(REPO_ROOT), size_mb, time.monotonic() - t0,
        )


async def _poll_until_done(http: httpx.AsyncClient, slug: str, video_id: str) -> str:
    """Block until Hera reports success; return file_url."""
    waited = 0
    last_status: str | None = None
    while waited <= POLL_TIMEOUT_S:
        r = await http.get(f"/videos/{video_id}")
        r.raise_for_status()
        body = r.json()
        status = body.get("status")
        outputs = body.get("outputs") or []
        if status != last_status:
            log.info("[%s] poll t=%ds status=%s outputs=%d", slug, waited, status, len(outputs))
            last_status = status
        if status == "success":
            file_url = (outputs[0] or {}).get("file_url")
            if not file_url:
                raise RuntimeError(f"[{slug}] success but no file_url in {outputs}")
            return file_url
        if status == "failed":
            err = (outputs[0] or {}).get("error") or "(no error message)"
            raise RuntimeError(f"[{slug}] Hera failed: {err}")
        await asyncio.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S
    raise RuntimeError(f"[{slug}] timed out after {POLL_TIMEOUT_S}s")


async def _download(http: httpx.AsyncClient, url: str, dest: Path) -> None:
    """Stream-download `url` into `dest`."""
    async with http.stream("GET", url) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            async for chunk in r.aiter_bytes(chunk_size=64 * 1024):
                f.write(chunk)


async def main_async(slugs: list[str], duration: int | None) -> int:
    for slug in slugs:
        try:
            await render_listing(slug, LISTINGS[slug], duration=duration)
        except Exception as exc:
            log.exception("[%s] render failed: %s", slug, exc)
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Argus landing-page Hera videos")
    parser.add_argument(
        "slug", nargs="?", default="all",
        choices=["all", *LISTINGS.keys()],
        help="Which listing to render (default: all)",
    )
    parser.add_argument(
        "--duration", type=int, default=None,
        help="Override duration_seconds (default: per-slug from SLUG_DURATION_DEFAULT — hero=30s with brand wrap, demo=25s)",
    )
    args = parser.parse_args()

    slugs = list(LISTINGS.keys()) if args.slug == "all" else [args.slug]
    return asyncio.run(main_async(slugs, args.duration))


if __name__ == "__main__":
    sys.exit(main())
