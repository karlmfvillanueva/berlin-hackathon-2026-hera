# ruff: noqa: E501
"""Strategic Opinion Agent — final Hera video prompt assembly.

Consumes structured outputs from ICP Classifier, Location Enrichment,
Reviews Evaluation, Visual Systems, and Photo Analyser plus listing summary.
Photo Analyser supplies the shortlist of up to five reference images; this
agent writes the executable Hera brief and 1-based indices into that shortlist
via Gemini structured output (response_schema).

Auth: Application Default Credentials (ADC) on Vertex AI. Requires GCP_PROJECT;
GCP_LOCATION defaults to us-central1.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from google import genai
from google.genai import types

from src.agent.models import Photo, ScrapedListing
from src.logger import log

_MODEL = os.getenv("GEMINI_FINAL_ASSEMBLY_MODEL", "gemini-2.5-pro")
# 2.5-Pro is a reasoning model: max_output_tokens covers thinking + JSON response.
_MAX_OUTPUT_TOKENS = 24000
_THINKING_BUDGET = 2048
_TEMPERATURE = 0.55  # baseline kept for reference; multi-sample uses _TEMPERATURES.

# Multi-sample + Judge settings. Three parallel Final-Assembly calls at
# different temperatures explore creative variance; a separate Judge agent
# scores them on five editorial criteria and picks the winner.
# Set ENABLE_MULTI_SAMPLE_JUDGE=false to fall back to a single 0.55 sample.
_TEMPERATURES: tuple[float, ...] = (0.55, 0.75, 0.95)
_JUDGE_MODEL = os.getenv("GEMINI_JUDGE_MODEL", "gemini-2.5-pro")
_JUDGE_TEMPERATURE = 0.2
_JUDGE_MAX_OUTPUT_TOKENS = 6000
_JUDGE_THINKING_BUDGET = 1024
_MULTI_SAMPLE_ENABLED = os.getenv("ENABLE_MULTI_SAMPLE_JUDGE", "true").lower() not in (
    "0",
    "false",
    "no",
)

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

DURATION DECISION

Choose duration_seconds: an integer in 15–45. Decide first, then build the
SCENE PLAN around it. Default landing zone 20–30s; 25s is the sweet spot.

- 15–20s: simple listing, single dominant attribute (urban studio, party
  rental). Hit fast, leave hungry.
- 20–30s (default): most listings. Enough room for hook → context → core →
  payoff → proof → CTA without rushing. Pick 25s when in doubt.
- 30–45s: only when the listing has multiple distinct conversion-driving
  facets for the chosen ICP (e.g. nomad: workspace + living + rooftop +
  neighborhood). Justify the extra runtime in CONVERSION PSYCHOLOGY.

duration_seconds (your choice) MUST equal the total of the SCENE PLAN times
exactly.

OUTPUT FORMAT (inside hera_video_prompt string only)

Output a SINGLE Hera-ready video prompt in the response schema field hera_video_prompt.
It must be directly usable for create_video — no preamble, no meta-commentary outside that string.

Structure hera_video_prompt EXACTLY with these sections and headings (keep headings as written):

Create a {duration_seconds} second vertical motion graphics video (9:16, 1080×1920).
Optimised for Instagram Reels and TikTok. Sound on.

(Substitute the integer you chose — e.g. "Create a 25 second…")

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

Six scenes summing exactly to duration_seconds. Use this proportional
allocation as the default; adjust if a specific scene needs more or less,
but every scene must have non-zero duration:

  SCENE 1 — HOOK              ~15% of total
  SCENE 2 — LOCATION / CONTEXT ~15%
  SCENE 3 — CORE EXPERIENCE    ~25%
  SCENE 4 — FEATURE PAYOFF     ~20%
  SCENE 5 — SOCIAL PROOF / CLIMAX ~15%
  SCENE 6 — CTA                ~10%

Spell out the actual start–end seconds for each scene (one decimal place).
Example for duration_seconds=25:
  SCENE 1 — HOOK (0.0–3.5s)
  SCENE 2 — LOCATION / CONTEXT (3.5–7.0s)
  SCENE 3 — CORE EXPERIENCE (7.0–13.0s)
  SCENE 4 — FEATURE PAYOFF (13.0–18.0s)
  SCENE 5 — SOCIAL PROOF / CLIMAX (18.0–22.0s)
  SCENE 6 — CTA (22.0–25.0s)

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

STRUCTURED OUTPUT

You MUST fill three response-schema fields:
- duration_seconds: integer in 15–45, matching the SCENE PLAN total exactly.
- hera_video_prompt: the full structured brief above as a single string.
- reference_photo_indices: array of 1-based indices into PROPERTY_PHOTOS
  (the Photo Analyser shortlist order in the user message). Use 1–N distinct
  indices max (N = number of photos in PROPERTY_PHOTOS), hero first. These
  are the images Hera will receive as references."""


_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "duration_seconds": {
            "type": "integer",
            "description": (
                "Total video length in seconds. Range 15–45; default landing zone 20–30; "
                "25 is the sweet spot. Must equal the SCENE PLAN total exactly."
            ),
            "minimum": 15,
            "maximum": 45,
        },
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
    "required": ["duration_seconds", "hera_video_prompt", "reference_photo_indices"],
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
    duration = result.get("duration_seconds")
    if not isinstance(duration, int) or not (15 <= duration <= 45):
        raise RuntimeError(
            f"duration_seconds must be an integer in [15, 45], got {duration!r}"
        )
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


_JUDGE_SYSTEM_PROMPT = """You are the Editorial Judge for short-form property listing videos.

Three Strategic Opinion Agents have each independently produced a Hera-ready
video brief for the SAME listing and ICP. They were given the same upstream
inputs but different temperatures, so they differ in creative angle, hook
phrasing, scene plan, and rejected personas.

Your job: evaluate each brief on five criteria, score them 0–10, and PICK
THE SINGLE STRONGEST brief for actually converting the target ICP. No ties.
No politeness. Pick the brief that would most clearly outperform a generic
Airbnb reel for THIS listing.

CRITERIA (each scored 0–10)

1. icp_alignment
   Does the brief mathematically target the ICP best_persona's
   `booking_trigger` and `emotional_driver` from the ICP context? Or does
   it drift to a generic guest? 10 = laser-focused on the persona's actual
   booking psychology. 0 = could be any persona.

2. hook_strength
   Would the OPENING HOOK LINE stop a thumb mid-scroll on TikTok/Reels?
   Concrete, sensory, specific to THIS listing? 10 = sharp and unique.
   0 = generic "Welcome to your Berlin getaway!" cliché.

3. specificity
   Does the brief use concrete details from the listing (named rooms,
   amenities, location landmarks, real review quotes when present) or
   does it lean on filler ("stylish", "cozy", "perfect")? 10 = every
   sentence references something verifiable in the listing context.
   0 = template-shaped prose.

4. rejection_clarity
   Are REJECTED PERSONAS explicit and commercially honest? Does the brief
   refuse to be everything to everyone? 10 = sharp rejections grounded in
   layout/amenity/location facts. 0 = vague or absent rejections.

5. conversion_focus
   Are WHAT TO PUSH and WHAT TO HIDE specific and persona-tied? Does
   CONVERSION PSYCHOLOGY explain why this angle wins for the ICP? 10 =
   you could hand it to a media buyer. 0 = generic do's-and-don'ts.

WORKFLOW

For EACH brief (in input order, index = 0, 1, 2 if three were provided):
- Score the five criteria honestly. Don't anchor to the average — call out
  weaknesses sharply.
- Compute aggregate = mean of the five scores (one decimal place).
- Write a one-line `weakness` describing the biggest flaw of THIS brief.

Then pick winner_index = the index of the brief with the highest aggregate.
If two briefs tie, pick the one with stronger hook_strength; if still tied,
pick the lower index. Set winner_score = that brief's aggregate.

In `rationale`, explain in 1–3 sentences why the winner beats the others.
Reference specific differences (e.g. "Brief 1's hook names the workspace
explicitly while Brief 0 hedges with 'a quiet space to focus'").

Output strict structured JSON matching the response schema, no preamble."""


_JUDGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "winner_index": {
            "type": "integer",
            "description": "0-based index of the strongest brief.",
            "minimum": 0,
        },
        "winner_score": {
            "type": "number",
            "description": "Aggregate score of the winner (0–10).",
            "minimum": 0.0,
            "maximum": 10.0,
        },
        "rationale": {
            "type": "string",
            "description": "1–3 sentences: why the winner beats the others (cite specifics).",
        },
        "scores_per_brief": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "minimum": 0},
                    "icp_alignment": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                    "hook_strength": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                    "specificity": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                    "rejection_clarity": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                    "conversion_focus": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                    "aggregate": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                    "weakness": {"type": "string"},
                },
                "required": [
                    "index",
                    "icp_alignment",
                    "hook_strength",
                    "specificity",
                    "rejection_clarity",
                    "conversion_focus",
                    "aggregate",
                    "weakness",
                ],
            },
        },
    },
    "required": ["winner_index", "winner_score", "rationale", "scores_per_brief"],
}


def _check_gcp_env() -> tuple[str, str]:
    project = os.getenv("GCP_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    if not project:
        raise RuntimeError("GCP_PROJECT is not set")
    return project, location


def _one_sample(
    listing: ScrapedListing,
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
    visual_system: Mapping[str, Any],
    photo_analysis: Mapping[str, Any],
    assembly_photos: list[Photo],
    temperature: float,
) -> dict[str, Any] | None:
    """Single Final-Assembly Gemini call. Returns the validated result dict or
    None if the call or validation failed (so callers can drop and continue).
    """
    project, location = _check_gcp_env()
    client = genai.Client(vertexai=True, project=project, location=location)
    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=_build_user_message(
                listing,
                icp,
                location_enrichment,
                reviews_evaluation,
                visual_system,
                photo_analysis,
                assembly_photos,
            ),
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_RESPONSE_SCHEMA,
                temperature=temperature,
                max_output_tokens=_MAX_OUTPUT_TOKENS,
                thinking_config=types.ThinkingConfig(thinking_budget=_THINKING_BUDGET),
            ),
        )
    except Exception as exc:
        log.warning("final_assembly: sample T=%.2f api error: %s", temperature, exc)
        return None

    raw = response.text
    if not raw:
        log.warning("final_assembly: sample T=%.2f returned empty response", temperature)
        return None
    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("final_assembly: sample T=%.2f invalid JSON: %s", temperature, exc)
        return None
    try:
        _validate_tool_result(result, assembly_photos)
    except RuntimeError as exc:
        log.warning("final_assembly: sample T=%.2f validation failed: %s", temperature, exc)
        return None

    log.info(
        "final_assembly: sample T=%.2f ok duration=%d prompt_chars=%d",
        temperature,
        result["duration_seconds"],
        len(str(result["hera_video_prompt"])),
    )
    return result


def _build_judge_user_message(
    samples: list[dict[str, Any]],
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
) -> str:
    """Numbered briefs + the editorial context they should be evaluated against."""
    best_icp = (icp.get("best_icp") or {}) if isinstance(icp, Mapping) else {}
    rev_summary = (
        (reviews_evaluation.get("review_summary") or {})
        if isinstance(reviews_evaluation, Mapping)
        else {}
    )
    loc_summary = (
        (location_enrichment.get("location_summary") or {})
        if isinstance(location_enrichment, Mapping)
        else {}
    )
    context = {
        "ICP_BEST_PERSONA": {
            "persona": best_icp.get("persona"),
            "booking_trigger": best_icp.get("booking_trigger"),
            "emotional_driver": best_icp.get("emotional_driver"),
            "fit_score": best_icp.get("fit_score"),
        },
        "LOCATION_HEADLINE": loc_summary.get("headline"),
        "REVIEWS_SUMMARY": {
            "overall_sentiment": rev_summary.get("overall_sentiment"),
            "most_repeated_positive_theme": rev_summary.get("most_repeated_positive_theme"),
            "most_repeated_negative_theme": rev_summary.get("most_repeated_negative_theme"),
        },
    }
    body_briefs = []
    for i, s in enumerate(samples):
        body_briefs.append(
            {
                "index": i,
                "duration_seconds": s.get("duration_seconds"),
                "hera_video_prompt": s.get("hera_video_prompt"),
            }
        )
    payload = {"CONTEXT": context, "BRIEFS": body_briefs}
    return (
        "Evaluate the following Strategic-Opinion briefs and pick the strongest "
        "for the given ICP and listing context.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _judge_briefs(
    samples: list[dict[str, Any]],
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Score the candidate briefs and return judge metadata, or None on failure."""
    project, location = _check_gcp_env()
    client = genai.Client(vertexai=True, project=project, location=location)
    try:
        response = client.models.generate_content(
            model=_JUDGE_MODEL,
            contents=_build_judge_user_message(
                samples, icp, location_enrichment, reviews_evaluation
            ),
            config=types.GenerateContentConfig(
                system_instruction=_JUDGE_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_JUDGE_RESPONSE_SCHEMA,
                temperature=_JUDGE_TEMPERATURE,
                max_output_tokens=_JUDGE_MAX_OUTPUT_TOKENS,
                thinking_config=types.ThinkingConfig(thinking_budget=_JUDGE_THINKING_BUDGET),
            ),
        )
    except Exception as exc:
        log.warning("final_assembly: judge api error: %s", exc)
        return None

    raw = response.text
    if not raw:
        log.warning("final_assembly: judge returned empty response")
        return None
    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("final_assembly: judge invalid JSON: %s", exc)
        return None

    winner = result.get("winner_index")
    if not isinstance(winner, int) or not (0 <= winner < len(samples)):
        log.warning(
            "final_assembly: judge winner_index=%r out of range for %d briefs",
            winner,
            len(samples),
        )
        return None
    score = result.get("winner_score")
    if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 10.0):
        log.warning("final_assembly: judge winner_score=%r out of range", score)
        return None
    rationale = result.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        log.warning("final_assembly: judge rationale missing")
        return None
    scores = result.get("scores_per_brief")
    if not isinstance(scores, list):
        log.warning("final_assembly: judge scores_per_brief missing")
        return None

    return result


def assemble_strategic_hera_prompt(
    listing: ScrapedListing,
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
    visual_system: Mapping[str, Any],
    photo_analysis: Mapping[str, Any],
) -> tuple[str, list[str], int, dict[str, Any] | None]:
    """Run Strategic Opinion assembly with 3 parallel samples + Judge.

    Returns ``(hera_prompt, selected_image_urls, duration_seconds, judge_meta)``.
    `judge_meta` is None when only one sample survived (no judging needed),
    when the Judge call failed (pipeline falls back to first survivor), or
    when the multi-sample path is disabled via env (single-sample mode).
    """
    assembly_photos = _photos_for_assembly(listing, photo_analysis)
    if not assembly_photos:
        raise RuntimeError("Final assembly requires at least one listing photo for Hera references")

    log.info(
        "final_assembly: calling %s shortlist_photos=%d multi_sample=%s",
        _MODEL,
        len(assembly_photos),
        _MULTI_SAMPLE_ENABLED,
    )

    temperatures: tuple[float, ...] = _TEMPERATURES if _MULTI_SAMPLE_ENABLED else (_TEMPERATURE,)

    samples: list[dict[str, Any] | None]
    if len(temperatures) == 1:
        samples = [
            _one_sample(
                listing,
                icp,
                location_enrichment,
                reviews_evaluation,
                visual_system,
                photo_analysis,
                assembly_photos,
                temperatures[0],
            )
        ]
    else:
        with ThreadPoolExecutor(max_workers=len(temperatures)) as pool:
            futures = [
                pool.submit(
                    _one_sample,
                    listing,
                    icp,
                    location_enrichment,
                    reviews_evaluation,
                    visual_system,
                    photo_analysis,
                    assembly_photos,
                    t,
                )
                for t in temperatures
            ]
            samples = [f.result() for f in futures]

    survivors: list[tuple[float, dict[str, Any]]] = [
        (t, s) for t, s in zip(temperatures, samples, strict=False) if s is not None
    ]
    if not survivors:
        raise RuntimeError("final_assembly: all samples failed (no usable brief)")

    judge_meta: dict[str, Any] | None = None
    chosen: dict[str, Any]

    if len(survivors) == 1:
        log.info("final_assembly: only one survivor, skipping judge")
        chosen = survivors[0][1]
    else:
        survivor_briefs = [s for _, s in survivors]
        judge_result = _judge_briefs(
            survivor_briefs, icp, location_enrichment, reviews_evaluation
        )
        if judge_result is None:
            log.warning("final_assembly: judge failed; falling back to first survivor")
            chosen = survivors[0][1]
        else:
            winner_idx = int(judge_result["winner_index"])
            chosen = survivor_briefs[winner_idx]
            judge_meta = {
                "winner_score": float(judge_result["winner_score"]),
                "rationale": str(judge_result["rationale"]).strip(),
                "scores_per_brief": list(judge_result["scores_per_brief"]),
                "winner_temperature": survivors[winner_idx][0],
                "candidates": len(survivors),
            }
            log.info(
                "final_assembly: judge selected winner=%d (T=%.2f) score=%.2f",
                winner_idx,
                survivors[winner_idx][0],
                judge_meta["winner_score"],
            )

    duration = int(chosen["duration_seconds"])
    prompt = str(chosen["hera_video_prompt"]).strip()
    selected = urls_from_indices(list(assembly_photos), chosen["reference_photo_indices"])

    log.info(
        "final_assembly: done duration_seconds=%d prompt_chars=%d reference_images=%d "
        "judged=%s",
        duration,
        len(prompt),
        len(selected),
        judge_meta is not None,
    )
    return prompt, selected, duration, judge_meta
