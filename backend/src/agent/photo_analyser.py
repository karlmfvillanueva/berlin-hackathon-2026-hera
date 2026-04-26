# ruff: noqa: E501
"""Photo Analyser agent for Airbnb scrape JSON.

Consumes ``presentation.photo_assets`` from the scrape plus structured outputs
from ICP, Location, and Reviews agents. Uses Gemini vision on hosted image URLs
where possible, scores every asset for conversion video use, rejects weak shots,
and returns exactly five hero-first indices (or fewer if the listing has fewer
than five photos) for Final Assembly + Hera reference URLs.

Auth: Application Default Credentials (ADC) on Vertex AI. Requires GCP_PROJECT;
GCP_LOCATION defaults to us-central1.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from google import genai
from google.genai import types

from src.logger import log

_MODEL = os.getenv("GEMINI_PHOTO_ANALYSER_MODEL", "gemini-2.5-pro")
# 2.5-Pro is a reasoning model: max_output_tokens covers thinking + JSON response.
_MAX_OUTPUT_TOKENS = 16000
_THINKING_BUDGET = 2048
_TEMPERATURE = 0.3
_MAX_VISION_ATTACHMENTS = 15

_SCORE = {"type": "number", "description": "0.0–1.0", "minimum": 0.0, "maximum": 1.0}
_RISK = {"type": "string", "enum": ["low", "medium", "high"]}
_ROLE = {
    "type": "string",
    "enum": [
        "hero_hook",
        "space_story",
        "amenity_proof",
        "location_context",
        "vibe_atmosphere",
        "social_proof_visual",
        "detail_payoff",
        "reject",
    ],
}

_SYSTEM_PROMPT = """You are the Photo Analyser Agent for short-term rental vertical video ads.

Your job is NOT to write the video script.

Your job is NOT to pick typography, colours, or music.

Your job is to answer: "Which five images from this listing should Hera receive as reference
frames, in what order, and why each wins or loses for conversion?"

You are a performance-creative image analyst: composition, lighting, credibility, ICP fit,
and narrative sequencing for a 12–15 second ad. You must be opinionated and commercially honest.

INPUTS (embedded in the user message)

1) PHOTO_CATALOG — every listing photo with 1-based index, URL, alt/caption text.
2) ICP_CLASSIFIER — who we are selling to; photos must flatter THAT guest, not a generic tourist.
3) LOCATION_ENRICHMENT — what "here" means emotionally; pick frames that support that story.
4) REVIEWS_EVALUATION — what guests actually praise or complain about; avoid visuals that contradict
   strong review themes or highlight review-flagged weaknesses.

VISION

When image pixels are attached, they appear in the SAME order as indices 1..N for the first N
attachments (N stated in the text bundle). Use pixels for composition, clutter, staging quality,
lighting honesty, and "TikTok first frame" stopping power.

If the catalog lists more photos than attached pixels, you may still SELECT any index from the
full PHOTO_CATALOG using URL + alt_text + strategic inference — but prefer vision-backed decisions
when you have pixels for that index.

SELECTION RULES

- Return exactly five DISTINCT 1-based indices when there are at least five photos; if there are
  fewer than five photos, return one entry per photo (all distinct), best story order.
- Order is hero-first: index[0] is the single best hook frame for the target ICP.
- Reject duplicate angles (e.g. three near-identical sofa wide shots); prefer diversity that
  matches the scene arc: hook → context → core space → payoff → proof/climax.
- Do NOT select images that look misleading vs reviews (e.g. ultra-wide lens making a tiny room
  look huge when reviews stress "cozy/small").
- Penalise heavy watermarks, extreme darkness, messy staging, toilet-forward compositions, and
  generic building exteriors unless location agent makes exterior the differentiator.
- Alt text is a weak signal vs pixels; do not override obvious pixel evidence with marketing copy.

OUTPUT QUALITY

Per-photo assessments must read like a creative strategist defending picks under scrutiny — not
generic labels. Rejected photos must have sharp, specific reasons.

Output strict structured JSON matching the response schema, no preamble."""


_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis_summary": {
            "type": "object",
            "properties": {
                "one_line_strategy": {
                    "type": "string",
                    "description": "Single sentence: what visual story the five picks tell.",
                },
                "icp_visual_hypothesis": {
                    "type": "string",
                    "description": "How the target ICP reads these photos in 2 seconds.",
                },
                "biggest_visual_risk": {
                    "type": "string",
                    "description": "Largest mismatch, honesty risk, or gallery weakness to manage in edit.",
                },
                "gallery_cohesion_score": _SCORE,
            },
            "required": [
                "one_line_strategy",
                "icp_visual_hypothesis",
                "biggest_visual_risk",
                "gallery_cohesion_score",
            ],
        },
        "per_photo_scores": {
            "type": "array",
            "description": "One row per catalog index (all photos in PHOTO_CATALOG).",
            "items": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "1-based index into PHOTO_CATALOG order.",
                    },
                    "hook_stopping_power": _SCORE,
                    "composition_clarity": _SCORE,
                    "lighting_truthfulness": _SCORE,
                    "icp_alignment": _SCORE,
                    "review_consistency": _SCORE,
                    "conversion_role_if_selected": _ROLE,
                    "honesty_risk": _RISK,
                    "verdict": {
                        "type": "string",
                        "description": "One tight sentence: keep, demote, or reject for this campaign.",
                    },
                },
                "required": [
                    "index",
                    "hook_stopping_power",
                    "composition_clarity",
                    "lighting_truthfulness",
                    "icp_alignment",
                    "review_consistency",
                    "conversion_role_if_selected",
                    "honesty_risk",
                    "verdict",
                ],
            },
        },
        "rejected_gallery_strengths": {
            "type": "array",
            "description": "Strong reasons certain indices were excluded from the top five.",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "minimum": 1},
                    "reason": {"type": "string"},
                    "what_it_would_wrongly_signal": {"type": "string"},
                },
                "required": ["index", "reason", "what_it_would_wrongly_signal"],
            },
        },
        "selected_indices_hero_first": {
            "type": "array",
            "description": (
                "1-based indices into PHOTO_CATALOG; distinct; min(5, catalog size) items; "
                "best hook first."
            ),
            "items": {"type": "integer", "minimum": 1},
            "minItems": 1,
            "maxItems": 5,
        },
        "narrative_slot_plan": {
            "type": "array",
            "description": "Parallel to selected_indices_hero_first: scene job for each chosen frame.",
            "items": {
                "type": "object",
                "properties": {
                    "slot": {
                        "type": "string",
                        "enum": ["hook", "context", "core_experience", "payoff", "proof_or_climax"],
                    },
                    "index": {"type": "integer", "minimum": 1},
                    "on_screen_job": {
                        "type": "string",
                        "description": "What this frame must accomplish in the edit (one line).",
                    },
                },
                "required": ["slot", "index", "on_screen_job"],
            },
        },
        "creative_director_notes_for_assembly": {
            "type": "string",
            "description": "Non-negotiable guidance for the Strategic Opinion Agent / motion director.",
        },
    },
    "required": [
        "analysis_summary",
        "per_photo_scores",
        "rejected_gallery_strengths",
        "selected_indices_hero_first",
        "narrative_slot_plan",
        "creative_director_notes_for_assembly",
    ],
}


def _photo_catalog_from_scrape(scrape: Mapping[str, Any]) -> list[dict[str, Any]]:
    pres = scrape.get("presentation")
    if not isinstance(pres, dict):
        return []
    raw = pres.get("photo_assets")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        alt = item.get("alt_text")
        out.append(
            {
                "index": i,
                "url": url.strip(),
                "alt_text": alt.strip() if isinstance(alt, str) else "",
            }
        )
    return out


def _build_message_content(
    catalog: list[dict[str, Any]],
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
    emphasis_hints: list[str] | None = None,
    deemphasis_hints: list[str] | None = None,
) -> list:
    n = len(catalog)
    vision_n = min(n, _MAX_VISION_ATTACHMENTS)
    bundle: dict[str, Any] = {
        "PHOTO_CATALOG": catalog,
        "ICP_CLASSIFIER": icp,
        "LOCATION_ENRICHMENT": location_enrichment,
        "REVIEWS_EVALUATION": reviews_evaluation,
        "VISION_NOTE": (
            f"The next {vision_n} message parts are images in order of indices 1..{vision_n} "
            "matching PHOTO_CATALOG order. Remaining catalog rows are text-only."
        ),
    }
    if emphasis_hints or deemphasis_hints:
        bundle["USER_EMPHASIS"] = {
            "must_feature": emphasis_hints or [],
            "downplay": deemphasis_hints or [],
            "instruction": (
                "User-supplied steering: when scoring photos and choosing the "
                "five hero-first indices, upweight photos showing the "
                "must_feature subjects and downweight photos centered on the "
                "downplay subjects. Treat as a soft preference layered on top "
                "of ICP fit — never select objectively bad photos to satisfy "
                "the hint, but break ties in favor of must_feature."
            ),
        }
    text_part = (
        "Analyse listing photos for a high-converting short vertical rental ad.\n"
        f"{json.dumps(bundle, ensure_ascii=False, indent=2)}"
    )
    parts: list = [text_part]
    for row in catalog[:vision_n]:
        parts.append(types.Part.from_uri(file_uri=row["url"], mime_type="image/jpeg"))
    return parts


def _normalize_selected(indices: list[Any], n_photos: int) -> list[int]:
    if n_photos <= 0:
        return []
    cap = min(5, n_photos)
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
        if len(out) >= cap:
            break
    if len(out) < cap:
        for i in range(1, n_photos + 1):
            if i not in seen:
                seen.add(i)
                out.append(i)
                if len(out) >= cap:
                    break
    return out


def _validate_result(result: dict[str, Any], n_photos: int) -> None:
    if n_photos == 0:
        raise RuntimeError("Photo analyser requires at least one photo in the scrape")
    summary = result.get("analysis_summary")
    if not isinstance(summary, dict):
        raise RuntimeError("analysis_summary must be an object")
    for key in ("one_line_strategy", "icp_visual_hypothesis", "biggest_visual_risk"):
        if not isinstance(summary.get(key), str) or not str(summary[key]).strip():
            raise RuntimeError(f"analysis_summary.{key} must be a non-empty string")
    gcs = summary.get("gallery_cohesion_score")
    if not isinstance(gcs, (int, float)) or not (0.0 <= float(gcs) <= 1.0):
        raise RuntimeError("analysis_summary.gallery_cohesion_score must be a number 0–1")

    scores = result.get("per_photo_scores")
    if not isinstance(scores, list) or len(scores) != n_photos:
        raise RuntimeError("per_photo_scores must include exactly one entry per catalog photo")
    seen_idx: set[int] = set()
    for i, row in enumerate(scores):
        if not isinstance(row, dict):
            raise RuntimeError(f"per_photo_scores[{i}] must be an object")
        idx = row.get("index")
        if not isinstance(idx, int) or idx < 1 or idx > n_photos:
            raise RuntimeError(f"per_photo_scores[{i}].index must be in 1..{n_photos}")
        if idx in seen_idx:
            raise RuntimeError(f"duplicate per_photo_scores index: {idx}")
        seen_idx.add(idx)
        for fld in (
            "hook_stopping_power",
            "composition_clarity",
            "lighting_truthfulness",
            "icp_alignment",
            "review_consistency",
        ):
            v = row.get(fld)
            if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                raise RuntimeError(f"per_photo_scores[{i}].{fld} must be a number 0–1")
        if row.get("honesty_risk") not in ("low", "medium", "high"):
            raise RuntimeError(f"per_photo_scores[{i}].honesty_risk invalid")
        allowed_roles = frozenset(
            {
                "hero_hook",
                "space_story",
                "amenity_proof",
                "location_context",
                "vibe_atmosphere",
                "social_proof_visual",
                "detail_payoff",
                "reject",
            }
        )
        if row.get("conversion_role_if_selected") not in allowed_roles:
            raise RuntimeError(f"per_photo_scores[{i}].conversion_role_if_selected invalid")
        if not isinstance(row.get("verdict"), str) or not str(row["verdict"]).strip():
            raise RuntimeError(f"per_photo_scores[{i}].verdict must be a non-empty string")
    if seen_idx != set(range(1, n_photos + 1)):
        raise RuntimeError("per_photo_scores must cover every catalog index exactly once")

    rej = result.get("rejected_gallery_strengths")
    if not isinstance(rej, list):
        raise RuntimeError("rejected_gallery_strengths must be an array")
    # rejected_gallery_strengths is creative annotation for the rationale rail —
    # the actual photo selection is in selected_indices_hero_first. Gemini often
    # under-fills this list (returns 4 of 5 expected). Downgrade count check to
    # a warning so a slightly lazy LLM doesn't kill the pipeline; per-row shape
    # validation stays strict.
    expected_rejects = max(0, n_photos - min(5, n_photos))
    if len(rej) < expected_rejects:
        log.warning(
            "photo_analyser: rejected_gallery_strengths short (got %d, expected ≥%d) — "
            "proceeding without it as the rationale fallback",
            len(rej),
            expected_rejects,
        )
    for i, row in enumerate(rej):
        if not isinstance(row, dict):
            raise RuntimeError(f"rejected_gallery_strengths[{i}] must be an object")
        if not isinstance(row.get("index"), int):
            raise RuntimeError(f"rejected_gallery_strengths[{i}].index must be an integer")
        for k in ("reason", "what_it_would_wrongly_signal"):
            if not isinstance(row.get(k), str) or not str(row[k]).strip():
                raise RuntimeError(
                    f"rejected_gallery_strengths[{i}].{k} must be a non-empty string"
                )

    sel = result.get("selected_indices_hero_first")
    if not isinstance(sel, list):
        raise RuntimeError("selected_indices_hero_first must be an array")
    expected = min(5, n_photos)
    normalized = _normalize_selected(sel, n_photos)
    if len(normalized) != expected:
        raise RuntimeError(
            f"selected_indices_hero_first must resolve to {expected} distinct valid indices"
        )
    result["selected_indices_hero_first"] = normalized

    # narrative_slot_plan is creative guidance for Final Assembly — partial plans
    # still produce a usable Hera brief. Per-row validation stays strict, but
    # length-equality and full coverage are downgraded to log warnings so a
    # slightly off-by-one Gemini output doesn't kill the pipeline.
    slots = result.get("narrative_slot_plan")
    if not isinstance(slots, list) or not slots:
        raise RuntimeError("narrative_slot_plan must be a non-empty array")
    allowed_slots = frozenset({"hook", "context", "core_experience", "payoff", "proof_or_climax"})
    slot_indices: list[int] = []
    for i, row in enumerate(slots):
        if not isinstance(row, dict):
            raise RuntimeError(f"narrative_slot_plan[{i}] must be an object")
        if row.get("slot") not in allowed_slots:
            raise RuntimeError(f"narrative_slot_plan[{i}].slot invalid")
        idx = row.get("index")
        if not isinstance(idx, int) or idx not in set(normalized):
            raise RuntimeError(
                f"narrative_slot_plan[{i}].index must be one of selected_indices_hero_first"
            )
        slot_indices.append(idx)
        if not isinstance(row.get("on_screen_job"), str) or not str(row["on_screen_job"]).strip():
            raise RuntimeError(f"narrative_slot_plan[{i}].on_screen_job must be non-empty")
    if len(slots) != len(normalized) or sorted(slot_indices) != sorted(normalized):
        log.warning(
            "photo_analyser: narrative_slot_plan partial coverage (slots=%d, selected=%d, "
            "slot_idx=%s, selected_idx=%s) — proceeding with degraded plan",
            len(slots),
            len(normalized),
            sorted(slot_indices),
            sorted(normalized),
        )

    notes = result.get("creative_director_notes_for_assembly")
    if not isinstance(notes, str) or len(notes.strip()) < 40:
        raise RuntimeError(
            "creative_director_notes_for_assembly must be substantive (min ~40 chars)"
        )


def analyse_photos(
    scrape: Mapping[str, Any],
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
    reviews_evaluation: Mapping[str, Any],
    emphasis_hints: list[str] | None = None,
    deemphasis_hints: list[str] | None = None,
) -> dict[str, Any]:
    """Run Photo Analyser on scrape + upstream agent JSON.

    ``emphasis_hints`` and ``deemphasis_hints`` are user-supplied soft steering
    labels (amenity / landmark / feature names) folded into the prompt as a
    preference layer. Both default to no-ops, preserving pre-Phase-1-flow behaviour.

    Returns structured dict including ``selected_indices_hero_first`` (1-based, distinct,
    length min(5, number of photos)).

    Raises ``RuntimeError`` if the API fails or validation does not pass.
    """
    catalog = _photo_catalog_from_scrape(scrape)
    n = len(catalog)
    if n == 0:
        raise RuntimeError(
            "Photo analyser requires presentation.photo_assets with at least one URL"
        )

    project = os.getenv("GCP_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    if not project:
        raise RuntimeError("GCP_PROJECT is not set")

    listing_id = None
    groups = scrape.get("groups")
    if isinstance(groups, dict):
        core = groups.get("core_identifiers")
        if isinstance(core, dict):
            listing_id = core.get("listing_id")

    log.info(
        "photo_analyser: calling %s listing_id=%s catalog=%d vision_attach=%d emphasis=%d deemphasis=%d",
        _MODEL,
        listing_id,
        n,
        min(n, _MAX_VISION_ATTACHMENTS),
        len(emphasis_hints or []),
        len(deemphasis_hints or []),
    )

    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model=_MODEL,
        contents=_build_message_content(
            catalog,
            icp,
            location_enrichment,
            reviews_evaluation,
            emphasis_hints=emphasis_hints,
            deemphasis_hints=deemphasis_hints,
        ),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            thinking_config=types.ThinkingConfig(thinking_budget=_THINKING_BUDGET),
        ),
    )

    raw = response.text
    if not raw:
        raise RuntimeError("photo_analyser: Gemini returned empty response")

    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"photo_analyser: invalid JSON from Gemini: {exc}") from exc

    _validate_result(result, n)

    log.info(
        "photo_analyser: done listing_id=%s selected=%s",
        listing_id,
        result.get("selected_indices_hero_first"),
    )
    return result
