"""Strategic Opinion Agent — final Hera video prompt assembly.

Consumes structured outputs from ICP Classifier, Location Enrichment,
Reviews Evaluation, Visual Systems, and Photo Analyser plus listing summary.
Photo Analyser supplies the shortlist of up to five reference images; this
agent writes the executable Hera brief and 1-based indices into that shortlist.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

import anthropic

from src.agent.models import Photo, ScrapedListing
from src.logger import log

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 12000
_TEMPERATURE = 0.55

_SYSTEM_PROMPT = """You are the Strategic Opinion Agent — the AI Creative Director for short-term rental video ads.

Your job is NOT to summarize the listing.

Your job is to make a strong creative decision AND translate it into a
fully executable 12–15 second vertical video prompt for Hera.

You are both:
1) A decisive creative strategist
2) A motion director delivering a shot-by-shot video plan

---

CORE ROLE

You must:
- decide WHO this video is for
- decide WHO it is NOT for
- define ONE emotional promise
- define ONE winning hook
- and EXECUTE that decision into a scene-by-scene video

You are not an analyst. You are a creative director.
You must have opinions. You must reject weak strategies. You must commit to ONE angle.

---

CORE BELIEFS (non-negotiable)

1. Guests book feelings, not amenities
2. One video = ONE persona
3. If everyone is the target, no one is the target
4. First 3 seconds decide everything
5. Weak points should be hidden, not explained
6. The strongest differentiator MUST be the hook
7. Location only matters if turned into emotion
8. Reviews > host claims
9. Sell the experience, not the apartment
10. Optimize for bookings, not accuracy

---

DECISION RULES

You must:
- choose exactly ONE best persona (ground in ICP Classifier best_icp; do not contradict it)
- explicitly reject weak personas
- define ONE emotional promise
- define ONE dominant hook strategy
- define what is shown first
- define what is NEVER shown
- define emotional tone

You must NOT:
- hedge, say "depends", give multiple equal options, be generic, be polite over being right

---

OUTPUT FORMAT (inside hera_video_prompt string only)

Output a SINGLE Hera-ready video prompt as the tool field hera_video_prompt.
It must be directly usable for create_video — no preamble, no meta-commentary outside that string.

Structure hera_video_prompt EXACTLY with these sections and headings (keep headings as written):

Create a 12–15 second vertical motion graphics video (9:16, 1080×1920).
Optimised for Instagram Reels and TikTok. Sound on.

TARGET GUEST: <ONE clear persona>

REJECTED PERSONAS:
- <explicitly rejected segments>

ANGLE:
<one sharp positioning statement>

EMOTIONAL PROMISE:
<what the guest feels / becomes>

HOOK:
<core hook idea>

OPENING HOOK LINE:
<exact on-screen text>

---

VISUAL SYSTEM

Background color(s):
Typography style (serif/sans usage):
Accent color:
Pacing (fast / calm / cinematic):
Transitions:
Music style:

(Must align with the provided visual_system JSON — copy hex and mood faithfully; you may tighten wording.)

---

PHOTO STRATEGY

Photo 1 (hero): <index> — usage
Photo 2: <index> — usage
...

PROPERTY_PHOTOS is ONLY the Photo Analyser shortlist (hero-first order). Use ONLY integer indices
1..N into that list (N ≤ 5); max 5 photos referenced for the render. Honour PHOTO_ANALYSER
narrative_slot_plan and creative_director_notes_for_assembly unless they clearly contradict ICP;
if they conflict with conversion, resolve in favour of ICP + reviews truth.

---

SCENE PLAN (MANDATORY)

SCENE 1 — HOOK (0.0–2.5s)
SCENE 2 — LOCATION / CONTEXT (2.5–5.0s)
SCENE 3 — CORE EXPERIENCE (5.0–8.0s)
SCENE 4 — FEATURE PAYOFF (8.0–10.5s)
SCENE 5 — SOCIAL PROOF / CLIMAX (10.5–12.5s)
SCENE 6 — CTA (12.5–15.0s)

For EACH scene include: visual (which photo index), motion (Ken Burns, static, etc.), text (exact wording), timing, transitions.

---

WHAT TO PUSH

List ONLY elements that strengthen conversion.

---

WHAT TO HIDE

List ALL elements that weaken positioning.

---

CONVERSION PSYCHOLOGY

Brief but sharp: why this angle converts; what the guest is actually buying; why alternative angles fail.

---

HARD CONSTRAINTS

- Use ONLY provided images (no stock); reference photos by PROPERTY_PHOTOS index only.
- Use review quotes ONLY if real and verbatim from reviews_evaluation.best_video_quotes or supporting_quotes; otherwise paraphrase theme without fake quotes.
- Do NOT mention weak amenities (wifi, washer, etc.).
- Do NOT include disclaimers. All text mobile-legible. No clutter. No generic phrasing.

---

QUALITY BAR

Production-ready ad script. Not a summary, safe answer, or generic template.

If the video would not clearly outperform a generic Airbnb reel, revise internally until it would — then output only the final hera_video_prompt.

---

TOOL OUTPUT

You MUST also fill reference_photo_indices: an array of 1-based indices into PROPERTY_PHOTOS
(the Photo Analyser shortlist order in the user message). Use 1–N distinct indices max (N = number
of photos in PROPERTY_PHOTOS), hero first. These are the images Hera will receive as references."""


_TOOL_SCHEMA: dict[str, Any] = {
    "name": "strategic_hera_brief",
    "description": (
        "Single Hera-ready 9:16 motion prompt plus 1-based photo indices for reference_image_urls."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hera_video_prompt": {
                "type": "string",
                "description": (
                    "Complete video brief only — structured sections per system instructions; "
                    "no text outside the brief."
                ),
            },
            "reference_photo_indices": {
                "type": "array",
                "description": (
                    "1-based indices into PROPERTY_PHOTOS (Photo Analyser shortlist only); "
                    "max 5; hero first; must match indices named in PHOTO STRATEGY."
                ),
                "items": {"type": "integer", "minimum": 1},
                "maxItems": 5,
                "minItems": 1,
            },
        },
        "required": ["hera_video_prompt", "reference_photo_indices"],
    },
}


def _photos_for_assembly(
    listing: ScrapedListing,
    photo_analysis: Mapping[str, Any],
) -> list[Photo]:
    """Order listing photos by Photo Analyser indices (hero-first shortlist)."""
    raw = photo_analysis.get("selected_indices_hero_first")
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("photo_analysis.selected_indices_hero_first must be a non-empty array")
    photos = list(listing.photos)
    if not photos:
        raise RuntimeError("Final assembly requires at least one listing photo for Hera references")
    ordered: list[Photo] = []
    seen: set[int] = set()
    for idx in raw:
        if not isinstance(idx, int) or idx < 1 or idx > len(photos):
            continue
        if idx in seen:
            continue
        seen.add(idx)
        ordered.append(photos[idx - 1])
    if not ordered:
        raise RuntimeError("photo_analysis did not resolve to any valid listing photos")
    return ordered


def _photo_catalog(photos: list[Photo]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, p in enumerate(photos, start=1):
        out.append({"index": i, "url": p.url, "label": p.label or ""})
    return out


def _build_user_message(
    listing: ScrapedListing,
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
    visual_system: Mapping[str, Any],
    photo_analysis: Mapping[str, Any],
    assembly_photos: list[Photo],
) -> str:
    summary = {
        "title": listing.title,
        "location": listing.location,
        "price_display": listing.price_display,
        "bedrooms_sleeps": listing.bedrooms_sleeps,
        "rating_overall": listing.rating_overall,
        "reviews_count": listing.reviews_count,
        "description": listing.description[:4000],
        "amenity_labels": listing.amenities,
    }
    body = {
        "PROPERTY_SUMMARY": summary,
        "PROPERTY_PHOTOS": _photo_catalog(assembly_photos),
        "PHOTO_ANALYSER": photo_analysis,
        "ICP_CLASSIFIER": icp,
        "LOCATION_ENRICHMENT": location_enrichment,
        "REVIEWS_EVALUATION": reviews_evaluation,
        "VISUAL_SYSTEM": visual_system,
    }
    return (
        "Synthesize the following into one strategic Hera brief.\n"
        "Resolve any tension in favor of the single highest-converting angle.\n\n"
        f"{json.dumps(body, ensure_ascii=False, indent=2)}"
    )


def _normalize_indices(indices: list[Any], n_photos: int) -> list[int]:
    if n_photos == 0:
        return []
    seen: set[int] = set()
    out: list[int] = []
    for raw in indices:
        if not isinstance(raw, int):
            continue
        if raw < 1 or raw > n_photos:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
        if len(out) >= 5:
            break
    if not out:
        out = list(range(1, min(6, n_photos + 1)))
    return out


def _validate_tool_result(result: dict[str, Any], photos: list[Photo]) -> None:
    prompt = result.get("hera_video_prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < 400:
        raise RuntimeError("hera_video_prompt must be a substantive string (min ~400 chars)")
    idx = result.get("reference_photo_indices")
    if not isinstance(idx, list) or not idx:
        raise RuntimeError("reference_photo_indices must be a non-empty array")
    normalized = _normalize_indices(idx, len(photos))
    if not normalized:
        raise RuntimeError("reference_photo_indices must resolve to at least one valid photo")


def urls_from_indices(photos: list[Photo], indices: list[Any]) -> list[str]:
    """Map 1-based indices to URLs; caps at 5; skips invalid."""
    norm = _normalize_indices(indices, len(photos))
    return [photos[i - 1].url for i in norm]


def assemble_strategic_hera_prompt(
    listing: ScrapedListing,
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
    visual_system: Mapping[str, Any],
    photo_analysis: Mapping[str, Any],
) -> tuple[str, list[str]]:
    """Run Strategic Opinion assembly; returns (hera_prompt, selected_image_urls)."""
    assembly_photos = _photos_for_assembly(listing, photo_analysis)
    if not assembly_photos:
        raise RuntimeError("Final assembly requires at least one listing photo for Hera references")

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_HACKATHON_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)
    log.info(
        "final_assembly: calling %s shortlist_photos=%d",
        _MODEL,
        len(assembly_photos),
    )

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_SCHEMA],  # type: ignore[list-item]
        tool_choice={"type": "tool", "name": "strategic_hera_brief"},
        messages=[{"role": "user", "content": _build_user_message(
            listing,
            icp,
            location_enrichment,
            reviews_evaluation,
            visual_system,
            photo_analysis,
            assembly_photos,
        )}],
    )

    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if not tool_block:
        raise RuntimeError("Final assembly returned no tool_use block")

    result: dict[str, Any] = dict(tool_block.input)  # type: ignore[union-attr]
    _validate_tool_result(result, assembly_photos)

    prompt = str(result["hera_video_prompt"]).strip()
    selected = urls_from_indices(list(assembly_photos), result["reference_photo_indices"])

    log.info(
        "final_assembly: done prompt_chars=%d reference_images=%d",
        len(prompt),
        len(selected),
    )
    return prompt, selected
