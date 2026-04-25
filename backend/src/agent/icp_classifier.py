# ruff: noqa: E501
"""ICP Classifier agent for Airbnb scrape JSON.

Consumes the raw scrape document (see architecture airbnb-scrape schema / template)
and returns booking-psychology ICP classification as structured JSON via Gemini
structured output (response_schema).

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

_MODEL = os.getenv("GEMINI_ICP_CLASSIFIER_MODEL", "gemini-2.5-pro")
# 2.5-Pro is a reasoning model: max_output_tokens covers thinking + JSON response.
_MAX_OUTPUT_TOKENS = 5600
_THINKING_BUDGET = 2048
_TEMPERATURE = 0.35

ALLOWED_PERSONAS: tuple[str, ...] = (
    "Friend group celebration",
    "Party group",
    "Couples weekend break",
    "Solo traveler",
    "Digital nomad",
    "First-time city tourist",
    "Budget-smart traveler",
    "Luxury experience seeker",
    "Family visiting adult child",
)

_SYSTEM_PROMPT = """You are the ICP Classifier Agent for short-term rental video generation.

Your job is NOT to decide visual style.
Your job is NOT to choose colors, pacing, music, or creative direction.
Your job is only to answer: "Who is the highest-converting guest for this property?"

You are a booking psychology classifier. Not a designer. Not a creative director.
You classify the best customer. Nothing else.

YOUR TASK
1. Identify the strongest booking personas
2. Score each persona by real conversion likelihood
3. Explain why they fit
4. Reject weak personas
5. Identify the single strongest ICP

Do NOT think: "Who could stay here?"
Think: "Who is most likely to book fastest?"
This is a commercial decision. Not an inclusive audience list.

AVAILABLE PERSONAS — use ONLY these exact labels (no synonyms):
Friend group celebration | Party group | Couples weekend break | Solo traveler |
Digital nomad | First-time city tourist | Budget-smart traveler | Luxury experience seeker |
Family visiting adult child

CLASSIFICATION LOGIC (apply when scoring)
- Friend group celebration → birthdays, reunions, social stays, shared memories, group comfort
- Party group → nightlife-first, celebration-heavy, high-energy booking, social identity
- Couples weekend break → intimacy, romance, city-break comfort, emotional atmosphere
- Solo traveler → independence, exploration, simplicity, safe private comfort
- Digital nomad → productivity, long-stay usability, work comfort, reliable setup
- First-time city tourist → sightseeing efficiency, walkability, main attractions motivation
- Budget-smart traveler → value-for-money, practical decisions, honest comfort over luxury
- Luxury experience seeker → premium aesthetics, exclusivity, prestige, elevated experience
- Family visiting adult child → warm, practical, emotionally safe stay for parents/relatives
  visiting family in the city; comfort, ease, familiarity, trust over excitement

SCORING RULES (fit_score)
- 0.90–1.00 = obvious high-conversion ICP
- 0.75–0.89 = strong viable persona
- 0.55–0.74 = possible but weaker angle
- below 0.55 = reject (do not place in best_icp or secondary_personas; put in rejected_personas)

Reject weak personas. Do not be soft. Do not force bad fits. Be commercially honest.

IMPORTANT RULES
- Do NOT say "This could work for everyone", "It depends", or list broad generic groups.
- Do NOT force luxury if the listing is clearly budget.
- Do NOT force couples if shared bathroom or layout kills intimacy.
- Do NOT force family if layout/signals are nightlife-first.
- Do NOT confuse guest capacity with guest intent (e.g. 8 guests may mean party or friends, not family).
Think like a performance marketer.

Output strict structured JSON matching the response schema, no preamble."""


_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "best_icp": {
            "type": "object",
            "description": "Single strongest ICP; fit_score must be >= 0.75 unless scrape is too sparse.",
            "properties": {
                "persona": {
                    "type": "string",
                    "description": "One of the nine allowed persona labels exactly.",
                },
                "fit_score": {
                    "type": "number",
                    "description": "0.55–1.00; best ICP should be >= 0.75 when evidence allows.",
                },
                "why_it_wins": {
                    "type": "string",
                    "description": "Sharp, evidence-led reason this persona books this listing fastest.",
                },
                "booking_trigger": {
                    "type": "string",
                    "description": "Concrete trigger that closes the booking for this ICP.",
                },
                "emotional_driver": {
                    "type": "string",
                    "description": "Primary emotional motivation for this ICP here.",
                },
            },
            "required": [
                "persona",
                "fit_score",
                "why_it_wins",
                "booking_trigger",
                "emotional_driver",
            ],
        },
        "secondary_personas": {
            "type": "array",
            "description": "0–4 additional viable personas (fit_score 0.55–0.89), weaker than best.",
            "items": {
                "type": "object",
                "properties": {
                    "persona": {"type": "string"},
                    "fit_score": {"type": "number"},
                    "why_it_still_works": {"type": "string"},
                },
                "required": ["persona", "fit_score", "why_it_still_works"],
            },
            "maxItems": 4,
        },
        "rejected_personas": {
            "type": "array",
            "description": "Personas below 0.55 fit or wrong fit; be selective and honest.",
            "items": {
                "type": "object",
                "properties": {
                    "persona": {"type": "string"},
                    "why_it_fails": {"type": "string"},
                },
                "required": ["persona", "why_it_fails"],
            },
            "minItems": 3,
            "maxItems": 9,
        },
        "conversion_summary": {
            "type": "object",
            "properties": {
                "what_guest_is_really_booking": {"type": "string"},
                "what_they_do_not_care_about": {"type": "string"},
                "why_this_listing_converts_for_this_icp": {"type": "string"},
            },
            "required": [
                "what_guest_is_really_booking",
                "what_they_do_not_care_about",
                "why_this_listing_converts_for_this_icp",
            ],
        },
    },
    "required": ["best_icp", "secondary_personas", "rejected_personas", "conversion_summary"],
}


def _build_user_message(scrape: Mapping[str, Any]) -> str:
    payload = json.dumps(scrape, ensure_ascii=False, separators=(",", ":"))
    return (
        "INPUT: JSON-structured Airbnb listing scrape (full document).\n"
        "Classify ICPs only from fields present; do not invent amenities, layout, or reviews "
        "not supported by the scrape. If data is sparse, stay conservative but still pick one best_icp.\n\n"
        f"{payload}"
    )


def _persona_in_allowed(persona: str) -> bool:
    return persona in ALLOWED_PERSONAS


def _validate_result(result: dict[str, Any]) -> None:
    best = result.get("best_icp")
    if not isinstance(best, dict):
        raise RuntimeError("best_icp must be an object")
    persona = best.get("persona")
    if not isinstance(persona, str) or not _persona_in_allowed(persona):
        raise RuntimeError(f"best_icp.persona must be one of: {', '.join(ALLOWED_PERSONAS)}")
    score = best.get("fit_score")
    if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
        raise RuntimeError("best_icp.fit_score must be a number between 0 and 1")
    if float(score) < 0.55:
        raise RuntimeError("best_icp.fit_score must be at least 0.55")

    secondaries = result.get("secondary_personas")
    if not isinstance(secondaries, list):
        raise RuntimeError("secondary_personas must be an array")
    best_persona = str(persona)
    seen_secondary: set[str] = set()
    best_score = float(score)
    for i, item in enumerate(secondaries):
        if not isinstance(item, dict):
            raise RuntimeError(f"secondary_personas[{i}] must be an object")
        p = item.get("persona")
        if not isinstance(p, str) or not _persona_in_allowed(p):
            raise RuntimeError(f"secondary_personas[{i}].persona must be an allowed label")
        if p == best_persona:
            raise RuntimeError("secondary_personas must not repeat best_icp.persona")
        if p in seen_secondary:
            raise RuntimeError(f"duplicate secondary persona: {p}")
        seen_secondary.add(p)
        fs = item.get("fit_score")
        if not isinstance(fs, (int, float)) or not (0.0 <= float(fs) <= 1.0):
            raise RuntimeError(f"secondary_personas[{i}].fit_score must be a number 0–1")
        if float(fs) >= best_score:
            raise RuntimeError("secondary personas must score strictly below best_icp.fit_score")

    rejected = result.get("rejected_personas")
    if not isinstance(rejected, list) or len(rejected) < 3:
        raise RuntimeError("rejected_personas must include at least 3 entries")
    seen_rejected: set[str] = set()
    for i, item in enumerate(rejected):
        if not isinstance(item, dict):
            raise RuntimeError(f"rejected_personas[{i}] must be an object")
        p = item.get("persona")
        if not isinstance(p, str) or not _persona_in_allowed(p):
            raise RuntimeError(f"rejected_personas[{i}].persona must be an allowed label")
        if p == best_persona:
            raise RuntimeError("rejected_personas must not include best_icp.persona")
        if p in seen_secondary:
            raise RuntimeError(
                f"rejected_personas[{i}].persona must not duplicate a secondary_personas entry"
            )
        if p in seen_rejected:
            raise RuntimeError(f"duplicate rejected persona: {p}")
        seen_rejected.add(p)

    conv = result.get("conversion_summary")
    if not isinstance(conv, dict):
        raise RuntimeError("conversion_summary must be an object")
    for key in (
        "what_guest_is_really_booking",
        "what_they_do_not_care_about",
        "why_this_listing_converts_for_this_icp",
    ):
        if not isinstance(conv.get(key), str) or not str(conv[key]).strip():
            raise RuntimeError(f"conversion_summary.{key} must be a non-empty string")


def classify_icp(scrape: Mapping[str, Any]) -> dict[str, Any]:
    """Run the ICP Classifier on an Airbnb scrape dict.

    Returns a dict with keys: best_icp, secondary_personas, rejected_personas,
    conversion_summary — aligned with the agent output contract.

    Raises RuntimeError if the API fails or the model omits / violates validation.
    """
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

    log.info("icp_classifier: calling %s listing_id=%s", _MODEL, listing_id)

    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model=_MODEL,
        contents=_build_user_message(scrape),
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
        raise RuntimeError("icp_classifier: Gemini returned empty response")

    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"icp_classifier: invalid JSON from Gemini: {exc}") from exc

    _validate_result(result)

    log.info(
        "icp_classifier: done listing_id=%s persona=%r score=%s",
        listing_id,
        (result.get("best_icp") or {}).get("persona"),
        (result.get("best_icp") or {}).get("fit_score"),
    )
    return result
