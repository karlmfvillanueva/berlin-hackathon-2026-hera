"""Orchestrates the full multi-agent pipeline for one listing.

run(listing, outpaint_enabled=False) -> AgentDecision

Stages:
  1. Build a scrape-shaped document from ScrapedListing (shim).
  2. Stage 1 in parallel: classify_icp + enrich_location + evaluate_reviews.
  3. Stage 2 in parallel: derive_visual_system (needs icp + location) +
     analyse_photos (needs scrape + icp + location + reviews; vision-enabled).
  4. assemble_strategic_hera_prompt — Final Assembly Strategic Opinion Agent
     produces the Hera-ready prompt + chosen reference image URLs.
  5. Optional outpaint to 9:16 (preserves Phase 2 path).
  6. Derive legacy display fields (vibes / hook / pacing / angle / background)
     from the structured agent outputs so the existing frontend keeps working.
  7. Derive beliefs_applied as a deterministic audit trail by mapping the
     structured agent decisions to the seed beliefs in Supabase. The new
     pipeline already encodes most beliefs as hard-coded prompt heuristics
     (12-15s duration, CTA at end, hero-first photo order, palette-by-setting)
     — we observe what the agents actually decided and label which seed
     beliefs effectively shaped the result. No extra LLM call, no schema risk.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.agent.beliefs import fetch_beliefs
from src.agent.final_assembly import assemble_strategic_hera_prompt
from src.agent.icp_classifier import classify_icp
from src.agent.location_enrichment import enrich_location
from src.agent.models import AgentDecision, Belief, ScrapedListing
from src.agent.outpainter import outpaint_5_photos
from src.agent.photo_analyser import analyse_photos
from src.agent.reviews_evaluation import evaluate_reviews
from src.agent.visual_systems import derive_visual_system
from src.logger import log


def _listing_to_scrape_document(listing: ScrapedListing) -> dict[str, Any]:
    """Shape a ScrapedListing as the nested scrape JSON the agents expect.

    Mirrors the shim used in the original ai-orchestration branch so the ICP,
    Location, Reviews, and Photo agents can consume `groups.*` and
    `presentation.*` regardless of whether the upstream scraper is the simple
    Phase 2 scraper or a richer Phase 3 source.
    """
    return {
        "source": "scraped_listing_shim",
        "groups": {
            "core_identifiers": {
                "listing_id": listing.url,
                "url_canonical": listing.url,
            },
            "ratings_and_reviews": {
                "rating_overall": listing.rating_overall,
                "reviews_count": listing.reviews_count,
                "review_tags_ai": listing.review_tags,
            },
        },
        "presentation": {
            "title": listing.title,
            "location_subtitle": listing.location,
            "price_per_night_display": listing.price_display,
            "bedrooms_bathrooms_sleeps_line": listing.bedrooms_sleeps,
            "person_capacity": listing.person_capacity,
            "description_plain": listing.description,
            "amenity_labels": listing.amenities,
            "photo_assets": [{"url": p.url, "alt_text": p.label or ""} for p in listing.photos],
            "review_tags": listing.review_tags,
            "review_quotes_verbatim": listing.review_quotes,
            "unavailable_amenities": listing.unavailable_amenities,
        },
    }


def _extract_mood(s: Any) -> str:
    """From a string like 'Deep navy #0A1F44, contemplative dusk' return
    'contemplative dusk' — the part without a hex token."""
    if not isinstance(s, str):
        return ""
    parts = [p.strip() for p in s.replace("·", ",").split(",")]
    for part in parts:
        if "#" not in part and part:
            return part
    return ""


def _derive_legacy_fields(
    icp: dict[str, Any],
    location: dict[str, Any],
    reviews: dict[str, Any],
    visual: dict[str, Any],
    photo: dict[str, Any],
) -> dict[str, str]:
    """Project the structured multi-agent outputs onto the Phase 2 display fields
    (vibes/hook/pacing/angle/background) so the existing RationaleRail keeps
    rendering without contract changes."""
    best = icp.get("best_icp") or {}
    conv = icp.get("conversion_summary") or {}
    loc_summary = location.get("location_summary") or {}
    photo_summary = photo.get("analysis_summary") or {}
    creative = location.get("creative_translation") or {}

    # vibes: setting + dominant colour mood + accent mood
    vibes_parts = [
        str(visual.get("inferred_setting") or "").strip(),
        _extract_mood(visual.get("primary_background")),
        _extract_mood(visual.get("accent")),
    ]
    vibes = " · ".join(p for p in vibes_parts if p)[:200] or "—"

    hook = (
        creative.get("emotional_carrier_line")
        or best.get("booking_trigger")
        or best.get("why_it_wins")
        or "—"
    )
    pacing = str(visual.get("pacing") or "—")
    angle = (
        conv.get("what_guest_is_really_booking")
        or best.get("emotional_driver")
        or loc_summary.get("headline")
        or "—"
    )
    background = (
        photo_summary.get("one_line_strategy")
        or photo.get("creative_director_notes_for_assembly")
        or "—"
    )

    # Trim long strings; the frontend cards aren't designed for paragraphs.
    return {
        "vibes": vibes,
        "hook": str(hook)[:280],
        "pacing": str(pacing)[:280],
        "angle": str(angle)[:280],
        "background": str(background)[:280],
    }


def _derive_beliefs_applied(
    icp: dict[str, Any],
    visual: dict[str, Any],
    reviews: dict[str, Any],
    photo: dict[str, Any],
    duration_seconds: int,
    available_beliefs: list[Belief],
) -> list[str]:
    """Audit trail: map structured multi-agent outputs to seed-belief rule_keys.

    The new pipeline encodes most Phase 2 beliefs as hard-coded prompt
    heuristics (CTA at end, hero-first photo order, palette-by-setting).
    Duration is now agent-chosen (15–45s) so duration_15s is conditional.
    Filtered to rule_keys present in `available_beliefs` so additions/
    removals to the Supabase table flow through without code changes.

    Pure Python over already-validated structured outputs — adds no failure
    modes to the LLM pipeline.
    """
    available = {b.rule_key for b in available_beliefs}
    applied: list[str] = []

    def add(key: str) -> None:
        if key in available and key not in applied:
            applied.append(key)

    # Always-on — locked in by the new system's hard-coded prompt rules:
    add("cta_at_end")  # final_assembly SCENE 6 is always CTA
    add("hook_with_hero_shot")  # photo_analyser orders hero-first
    add("music_over_voiceover")  # visual_systems music field is always populated

    # Duration belief — only when the agent landed on the Phase-2 anchor.
    if duration_seconds == 15:
        add("duration_15s")

    persona = (icp.get("best_icp") or {}).get("persona") or ""
    setting = (visual.get("inferred_setting") or "").lower()
    pacing = (visual.get("pacing") or "").lower()

    # Setting-specific palette beliefs
    if setting == "coastal":
        add("warm_palette_for_beach")
    if setting == "city":
        add("minimal_palette_for_urban")

    # Pacing beliefs derived from visual_systems' pacing string
    if "fast" in pacing:
        add("fast_cuts_for_amenities")
    if "slow" in pacing:
        add("slow_reveal_for_hero")

    # Social proof — only credible if review quotes were extracted
    quotes = reviews.get("best_video_quotes")
    if isinstance(quotes, list) and quotes:
        add("social_proof_before_cta")

    # Persona-specific beliefs
    if persona == "Digital nomad":
        add("dedicated_workspace_hook")
    if persona == "Couples weekend break":
        add("couples_framing_first")

    return applied


async def run(listing: ScrapedListing, outpaint_enabled: bool = False) -> AgentDecision:
    """Run the full multi-agent pipeline and return a populated AgentDecision."""
    log.info("orchestrator: start listing=%s outpaint=%s", listing.url, outpaint_enabled)

    # Phase 2 beliefs are still pulled (kept for frontend display + future
    # injection into Final Assembly). Currently not consumed by the new pipeline,
    # so beliefs_applied stays empty.
    beliefs = fetch_beliefs(limit=10)
    log.info("orchestrator: beliefs_fetched=%d", len(beliefs))

    scrape = _listing_to_scrape_document(listing)

    # Stage 1 — three independent listing-intelligence agents, parallel.
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_icp = pool.submit(classify_icp, scrape)
        fut_loc = pool.submit(enrich_location, scrape)
        fut_reviews = pool.submit(evaluate_reviews, scrape)
        icp = fut_icp.result()
        location = fut_loc.result()
        reviews = fut_reviews.result()

    # Stage 2 — visual system (icp + location) and photo selection (scrape + all
    # three Stage 1 outputs, vision-backed). Parallel.
    with ThreadPoolExecutor(max_workers=2) as pool2:
        fut_visual = pool2.submit(
            derive_visual_system,
            icp=icp,
            location_enrichment=location,
        )
        fut_photo = pool2.submit(
            analyse_photos,
            scrape,
            icp,
            location,
            reviews,
        )
        visual = fut_visual.result()
        photo = fut_photo.result()

    # Final assembly — Strategic Opinion Agent runs 3 parallel samples,
    # Judge picks the strongest brief (judge_meta=None on single-sample path
    # or judge failure → caller falls back to first survivor inside the call).
    (
        hera_prompt,
        selected_image_urls,
        duration_seconds,
        judge_meta,
    ) = assemble_strategic_hera_prompt(
        listing=listing,
        icp=icp,
        location_enrichment=location,
        reviews_evaluation=reviews,
        visual_system=visual,
        photo_analysis=photo,
    )

    # Optional Phase 2 outpaint pass over the chosen reference URLs.
    if outpaint_enabled:
        selected_image_urls = await outpaint_5_photos(selected_image_urls)

    legacy = _derive_legacy_fields(icp, location, reviews, visual, photo)
    beliefs_applied = _derive_beliefs_applied(
        icp, visual, reviews, photo, duration_seconds, beliefs
    )

    decision = AgentDecision(
        vibes=legacy["vibes"],
        hook=legacy["hook"],
        pacing=legacy["pacing"],
        angle=legacy["angle"],
        background=legacy["background"],
        selected_image_urls=selected_image_urls,
        hera_prompt=hera_prompt,
        outpaint_enabled=outpaint_enabled,
        beliefs_applied=beliefs_applied,
        icp=icp,
        location_enrichment=location,
        reviews_evaluation=reviews,
        visual_system=visual,
        photo_analysis=photo,
        duration_seconds=duration_seconds,
        judge_score=judge_meta["winner_score"] if judge_meta else None,
        judge_rationale=judge_meta["rationale"] if judge_meta else None,
        judge_scores_per_brief=judge_meta["scores_per_brief"] if judge_meta else None,
    )

    best = icp.get("best_icp") if isinstance(icp.get("best_icp"), dict) else {}
    log.info(
        "orchestrator: done persona=%r inferred_setting=%r duration_s=%d images=%d "
        "prompt_chars=%d beliefs_applied=%d/%d",
        best.get("persona") if isinstance(best, dict) else None,
        visual.get("inferred_setting") if isinstance(visual, dict) else None,
        decision.duration_seconds,
        len(decision.selected_image_urls),
        len(decision.hera_prompt),
        len(decision.beliefs_applied),
        len(beliefs),
    )
    return decision
