"""Orchestrates the multi-agent pipeline for one listing, split into two phases.

Phase 1 — `run_storyboard_plan(listing, outpaint_enabled)` returns a Phase1Decision
the user can approve / override. Cheap (~10s on top of scrape):
  1. Stage 1 in parallel: classify_icp + enrich_location + evaluate_reviews.
  2. derive_visual_system (needs icp + location).
  3. _suggest_phase1_extras: language detection, tone preset, emphasis chips,
     hook candidates derived from the structured agent outputs above.

Phase 2 — `run_render_from_plan(listing, phase1, overrides)` returns the full
AgentDecision ready for Hera submission. Expensive (~10s + Hera 3 min):
  4. analyse_photos (vision-backed) — receives emphasis / deemphasis hints.
  5. assemble_strategic_hera_prompt — Strategic Opinion Agent receives user
     overrides (language, tone, emphasis, chosen hook) injected into the brief.
  6. Optional outpaint to 9:16.
  7. Derive legacy display fields + beliefs_applied audit trail.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.agent.beliefs import fetch_beliefs
from src.agent.final_assembly import assemble_strategic_hera_prompt
from src.agent.icp_classifier import classify_icp
from src.agent.location_enrichment import enrich_location
from src.agent.models import (
    AgentDecision,
    Belief,
    EmphasisOption,
    HookOption,
    Language,
    Overrides,
    Phase1Decision,
    ScrapedListing,
    Tone,
)
from src.agent.outpainter import outpaint_5_photos
from src.agent.photo_analyser import analyse_photos
from src.agent.reviews_evaluation import evaluate_reviews
from src.agent.visual_systems import derive_visual_system
from src.logger import log

# Persona → tone preset map. Drives suggested_tone in Phase 1; the user can
# override. Coverage of all nine ALLOWED_PERSONAS in icp_classifier.
_PERSONA_TONE: dict[str, Tone] = {
    "Luxury experience seeker": "luxury",
    "Family visiting adult child": "family",
    "Friend group celebration": "urban",
    "Party group": "urban",
    "Digital nomad": "urban",
    "First-time city tourist": "urban",
    "Couples weekend break": "cozy",
    "Solo traveler": "cozy",
    "Budget-smart traveler": "cozy",
}

# Tiny stop-word language detector. Avoids adding a new dependency. Counts
# distinct hits; thresholds tuned for short Airbnb-listing-length text.
_LANG_MARKERS: dict[Language, frozenset[str]] = {
    "de": frozenset(
        {"der", "die", "das", "und", "ist", "ein", "eine", "mit", "für", "wir", "sie", "auch"}
    ),
    "es": frozenset(
        {"el", "la", "los", "las", "y", "es", "un", "una", "con", "para", "que", "del"}
    ),
    "en": frozenset(
        {"the", "and", "is", "a", "an", "of", "to", "in", "with", "for", "you", "our"}
    ),
}


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


def _detect_language(text: str) -> Language:
    """Return the most-likely Language for short listing text.

    Pure heuristic over a small stop-word list — accurate enough for the three
    languages we expose and zero-dependency."""
    if not text:
        return "en"
    tokens = re.findall(r"[a-zäöüáéíóúñ']+", text.lower())[:600]
    if not tokens:
        return "en"
    counts: dict[Language, int] = {"de": 0, "es": 0, "en": 0}
    for tok in tokens:
        for lang, markers in _LANG_MARKERS.items():
            if tok in markers:
                counts[lang] += 1
    winner = max(counts, key=lambda k: counts[k])
    # Require at least 3 hits before claiming a non-English language; otherwise
    # default to English to avoid flipping on tiny noise.
    if winner != "en" and counts[winner] < 3:
        return "en"
    return winner


def _suggest_tone(icp: dict[str, Any]) -> Tone:
    persona = ((icp.get("best_icp") or {}).get("persona") or "") if isinstance(icp, dict) else ""
    return _PERSONA_TONE.get(persona, "cozy")


def _slugify(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return s or "item"


def _suggest_emphasis_options(
    listing: ScrapedListing,
    location: dict[str, Any],
    reviews: dict[str, Any],
    limit: int = 8,
) -> list[EmphasisOption]:
    """Top emphasis chips from amenities + landmarks + review-emphasis themes.

    Score = base weight per source + 0.5 per occurrence in review quotes. Slugs
    are stable ids the frontend echoes back in Overrides.emphasis."""
    quote_text = " ".join(listing.review_quotes or []).lower()

    candidates: dict[str, EmphasisOption] = {}

    def add(label: str, source: str, base_score: float) -> None:
        label = label.strip()
        if not label:
            return
        slug = _slugify(label)
        bonus = 0.5 * sum(1 for tok in label.lower().split() if len(tok) > 3 and tok in quote_text)
        score = base_score + bonus
        existing = candidates.get(slug)
        if existing is None or score > existing.score:
            candidates[slug] = EmphasisOption(slug=slug, label=label, score=score, source=source)  # type: ignore[arg-type]

    for amenity in listing.amenities or []:
        add(amenity, "amenity", base_score=1.0)

    landmarks = location.get("landmark_proximity") if isinstance(location, dict) else None
    if isinstance(landmarks, list):
        for lm in landmarks[:6]:
            if isinstance(lm, str):
                add(lm.split("—")[0].split("(")[0].strip(), "location", base_score=1.2)

    creative = reviews.get("creative_implications") if isinstance(reviews, dict) else None
    if isinstance(creative, dict):
        for theme in (creative.get("what_to_emphasize") or [])[:6]:
            if isinstance(theme, str):
                add(theme, "review", base_score=1.5)

    ranked = sorted(candidates.values(), key=lambda o: o.score, reverse=True)
    return ranked[:limit]


def _suggest_hook_options(
    listing: ScrapedListing,
    icp: dict[str, Any],
    location: dict[str, Any],
    reviews: dict[str, Any],
) -> list[HookOption]:
    """Three concrete hook candidates from the structured Stage 1 outputs."""
    hooks: list[HookOption] = []

    creative_imp = reviews.get("creative_implications") if isinstance(reviews, dict) else {}
    top_emphasis: str | None = None
    if isinstance(creative_imp, dict):
        emph = creative_imp.get("what_to_emphasize") or []
        if isinstance(emph, list) and emph:
            for e in emph:
                if isinstance(e, str) and e.strip():
                    top_emphasis = e.strip()
                    break
    if top_emphasis:
        hooks.append(
            HookOption(
                id="amenity-top",
                label=top_emphasis,
                kind="amenity",
                rationale="Reviews-validated angle: what guests already praise most.",
            )
        )

    if isinstance(location, dict):
        landmarks = location.get("landmark_proximity")
        if isinstance(landmarks, list):
            for lm in landmarks:
                if isinstance(lm, str) and lm.strip():
                    label = lm.split("—")[0].split("(")[0].strip()
                    hooks.append(
                        HookOption(
                            id="location-top",
                            label=label,
                            kind="location",
                            rationale="Open with the landmark guests are actually here for.",
                        )
                    )
                    break

    if isinstance(reviews, dict):
        quotes = reviews.get("best_video_quotes") or []
        if isinstance(quotes, list):
            for q in quotes:
                if isinstance(q, dict):
                    text = q.get("quote")
                    if isinstance(text, str) and text.strip():
                        snippet = text.strip()
                        if len(snippet) > 80:
                            snippet = snippet[:77].rstrip() + "…"
                        hooks.append(
                            HookOption(
                                id="review-top",
                                label=f"“{snippet}”",
                                kind="review",
                                rationale="Real guest words carry more trust than host claims.",
                            )
                        )
                        break

    if not hooks:
        best_icp = (icp.get("best_icp") or {}) if isinstance(icp, dict) else {}
        trigger = best_icp.get("booking_trigger") if isinstance(best_icp, dict) else None
        if isinstance(trigger, str) and trigger.strip():
            hooks.append(
                HookOption(
                    id="icp-trigger",
                    label=trigger.strip(),
                    kind="amenity",
                    rationale="The booking trigger of the strongest persona for this listing.",
                )
            )

    return hooks[:3]


def _suggest_phase1_extras(
    listing: ScrapedListing,
    icp: dict[str, Any],
    location: dict[str, Any],
    reviews: dict[str, Any],
) -> dict[str, Any]:
    language = _detect_language(f"{listing.title}\n{listing.description}")
    tone = _suggest_tone(icp)
    emphasis = _suggest_emphasis_options(listing, location, reviews)
    hooks = _suggest_hook_options(listing, icp, location, reviews)
    return {
        "language": language,
        "tone": tone,
        "emphasis": emphasis,
        "hooks": hooks,
    }


def run_storyboard_plan(
    listing: ScrapedListing,
    outpaint_enabled: bool = False,
) -> Phase1Decision:
    """Phase 1: scrape + cheap agents + suggestion layer for user approval."""
    log.info(
        "orchestrator: phase1 start listing=%s outpaint=%s", listing.url, outpaint_enabled
    )
    scrape = _listing_to_scrape_document(listing)

    # Stage 1 — three independent listing-intelligence agents, parallel.
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_icp = pool.submit(classify_icp, scrape)
        fut_loc = pool.submit(enrich_location, scrape)
        fut_reviews = pool.submit(evaluate_reviews, scrape)
        icp = fut_icp.result()
        location = fut_loc.result()
        reviews = fut_reviews.result()

    # Visual system depends on icp + location; ~2-3 s, kept in Phase 1 because
    # the user-facing tone preset reads from it indirectly.
    visual = derive_visual_system(icp=icp, location_enrichment=location)

    extras = _suggest_phase1_extras(listing, icp, location, reviews)

    phase1 = Phase1Decision(
        icp=icp,
        location_enrichment=location,
        reviews_evaluation=reviews,
        visual_system=visual,
        suggested_language=extras["language"],
        suggested_tone=extras["tone"],
        emphasis_options=extras["emphasis"],
        hook_options=extras["hooks"],
        duration_seconds=15,
        outpaint_enabled=outpaint_enabled,
    )
    log.info(
        "orchestrator: phase1 done persona=%r setting=%r tone=%s lang=%s "
        "emphasis=%d hooks=%d",
        ((icp.get("best_icp") or {}).get("persona") if isinstance(icp, dict) else None),
        (visual.get("inferred_setting") if isinstance(visual, dict) else None),
        phase1.suggested_tone,
        phase1.suggested_language,
        len(phase1.emphasis_options),
        len(phase1.hook_options),
    )
    return phase1


async def run_render_from_plan(
    listing: ScrapedListing,
    phase1: Phase1Decision,
    overrides: Overrides,
) -> AgentDecision:
    """Phase 2: heavy agents + final assembly with user overrides applied."""
    log.info(
        "orchestrator: phase2 start listing=%s lang=%s tone=%s emphasis=%d hook=%s outpaint=%s",
        listing.url,
        overrides.language,
        overrides.tone,
        len(overrides.emphasis),
        overrides.hook_id,
        phase1.outpaint_enabled,
    )

    icp = phase1.icp or {}
    location = phase1.location_enrichment or {}
    reviews = phase1.reviews_evaluation or {}
    visual = phase1.visual_system or {}

    beliefs = fetch_beliefs(limit=10)
    scrape = _listing_to_scrape_document(listing)

    photo = analyse_photos(
        scrape,
        icp,
        location,
        reviews,
        emphasis_hints=overrides.emphasis,
        deemphasis_hints=overrides.deemphasis,
    )

    chosen_hook: HookOption | None = None
    if overrides.hook_id and overrides.hook_id != "auto":
        for h in phase1.hook_options:
            if h.id == overrides.hook_id:
                chosen_hook = h
                break

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
        overrides=overrides,
        chosen_hook=chosen_hook,
    )

    if phase1.outpaint_enabled:
        selected_image_urls = await outpaint_5_photos(selected_image_urls)

    legacy = _derive_legacy_fields(icp, location, reviews, visual, photo)
    beliefs_applied = _derive_beliefs_applied(
        icp, visual, reviews, photo, duration_seconds, beliefs
    )

    # Tag overrides into beliefs_applied so RationaleRail can show them.
    overrides_tag = (
        f"override:lang={overrides.language},tone={overrides.tone},"
        f"emphasis={len(overrides.emphasis)},hook={overrides.hook_id}"
    )
    beliefs_applied = [*beliefs_applied, overrides_tag]

    decision = AgentDecision(
        vibes=legacy["vibes"],
        hook=legacy["hook"],
        pacing=legacy["pacing"],
        angle=legacy["angle"],
        background=legacy["background"],
        selected_image_urls=selected_image_urls,
        hera_prompt=hera_prompt,
        outpaint_enabled=phase1.outpaint_enabled,
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

    log.info(
        "orchestrator: phase2 done duration_s=%d images=%d prompt_chars=%d",
        decision.duration_seconds,
        len(decision.selected_image_urls),
        len(decision.hera_prompt),
    )
    return decision
