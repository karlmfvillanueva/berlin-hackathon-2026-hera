# ruff: noqa: E501
"""Location enrichment agent for Airbnb scrape JSON.

Consumes the raw scrape document (see architecture airbnb-scrape schema / template)
and returns booking-conversion-focused location insight as structured JSON via Gemini
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

_MODEL = os.getenv("GEMINI_LOCATION_ENRICHMENT_MODEL", "gemini-2.5-pro")
# 2.5-Pro is a reasoning model: max_output_tokens covers thinking + JSON response.
_MAX_OUTPUT_TOKENS = 6400
_THINKING_BUDGET = 2048
_TEMPERATURE = 0.35

_SYSTEM_PROMPT = """You are the Location Enrichment Agent for short-term rental video generation.

Your job is NOT to describe geography.

Your job is to explain why this location increases booking conversion.

You must translate raw location into guest-perceived emotional value.

Focus on:

- landmark proximity
- walkability value
- neighborhood identity
- trip occasion fit
- friction reducers
- location risks
- emotional positioning

RULES:

Do NOT use generic phrases like:

- great location
- centrally located
- perfect neighborhood
- close to everything

These are banned.

Always translate location into:
"How does this improve the guest's trip?"

Good:
"Guests can walk to Old Town Square in 5 minutes and avoid transport planning."

Bad:
"Very central location."

Output strict structured JSON matching the response schema, no preamble."""

# Response schema for Gemini structured output. Same shape as the original Anthropic
# tool input_schema; Gemini's google-genai SDK accepts JSON-Schema-compatible dicts on
# `response_schema` and returns matching JSON via `response.text`.
_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "location_summary": {
            "type": "object",
            "description": "Why this pin converts — guest trip payoff, not map facts.",
            "properties": {
                "headline": {
                    "type": "string",
                    "description": "One line: concrete conversion angle grounded in scrape data.",
                },
                "guest_trip_payoff": {
                    "type": "string",
                    "description": "How the stay gets easier or richer because of where it sits.",
                },
                "differentiator_vs_generic_stays": {
                    "type": "string",
                    "description": "What guests gain vs booking 'any place nearby'.",
                },
            },
            "required": ["headline", "guest_trip_payoff", "differentiator_vs_generic_stays"],
        },
        "landmark_proximity": {
            "type": "array",
            "description": "Specific landmarks/destinations + walk/transit + trip benefit each.",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10,
        },
        "walkability_value": {
            "type": "object",
            "description": "How walkability reduces planning stress or unlocks itinerary.",
            "properties": {
                "daily_rhythm_without_car": {"type": "string"},
                "planning_friction_removed": {"type": "string"},
                "concrete_examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 6,
                },
            },
            "required": [
                "daily_rhythm_without_car",
                "planning_friction_removed",
                "concrete_examples",
            ],
        },
        "neighborhood_identity": {
            "type": "object",
            "description": "Who this block feels for; social energy; identity guests buy into.",
            "properties": {
                "character_in_guest_words": {"type": "string"},
                "who_thrives_here": {"type": "string"},
                "social_energy": {"type": "string"},
            },
            "required": ["character_in_guest_words", "who_thrives_here", "social_energy"],
        },
        "best_trip_occasions": {
            "type": "array",
            "description": "Trip types where this location is a decisive win (specific).",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 8,
        },
        "friction_reducers": {
            "type": "array",
            "description": "Logistics pains this location removes (late arrival, jet lag, kids, etc.).",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10,
        },
        "location_risks": {
            "type": "array",
            "description": "Honest drawbacks or mitigations (noise, stairs, distance to X) — no burying risks.",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 8,
        },
        "creative_translation": {
            "type": "object",
            "description": "How to show/say location in vertical video without banned clichés.",
            "properties": {
                "on_screen_hook_ideas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 5,
                },
                "b_roll_or_map_direction": {"type": "string"},
                "emotional_carrier_line": {
                    "type": "string",
                    "description": "Single line voiceover or supers tone — outcome-led.",
                },
            },
            "required": [
                "on_screen_hook_ideas",
                "b_roll_or_map_direction",
                "emotional_carrier_line",
            ],
        },
    },
    "required": [
        "location_summary",
        "landmark_proximity",
        "walkability_value",
        "neighborhood_identity",
        "best_trip_occasions",
        "friction_reducers",
        "location_risks",
        "creative_translation",
    ],
}

_REQUIRED_TOP_LEVEL = {
    "location_summary",
    "landmark_proximity",
    "walkability_value",
    "neighborhood_identity",
    "best_trip_occasions",
    "friction_reducers",
    "location_risks",
    "creative_translation",
}


def _build_user_message(scrape: Mapping[str, Any]) -> str:
    payload = json.dumps(scrape, ensure_ascii=False, separators=(",", ":"))
    return (
        "Airbnb listing scrape JSON (full document). "
        "Infer location value only from fields present; do not invent addresses, distances, or venues "
        "not supported by the scrape. If data is sparse, say what is unknown and stay conservative.\n\n"
        f"{payload}"
    )


def _listing_id_from_scrape(scrape: Mapping[str, Any]) -> str | None:
    groups = scrape.get("groups")
    if not isinstance(groups, dict):
        return None
    core = groups.get("core_identifiers")
    if not isinstance(core, dict):
        return None
    raw = core.get("listing_id")
    return raw if isinstance(raw, str) else None


def enrich_location(scrape: Mapping[str, Any]) -> dict[str, Any]:
    """Run the Location Enrichment Agent on an Airbnb scrape dict.

    Returns a dict with keys:
    location_summary, landmark_proximity, walkability_value, neighborhood_identity,
    best_trip_occasions, friction_reducers, location_risks, creative_translation

    Raises RuntimeError if the API fails or the model omits required fields.
    """
    project = os.getenv("GCP_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    if not project:
        raise RuntimeError("GCP_PROJECT is not set")

    listing_id = _listing_id_from_scrape(scrape)
    log.info("location_enrichment: calling %s listing_id=%s", _MODEL, listing_id)

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
        raise RuntimeError(
            f"location_enrichment: Gemini returned empty response (finish_reason="
            f"{getattr(response.candidates[0], 'finish_reason', None) if response.candidates else None})"
        )

    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"location_enrichment: invalid JSON from Gemini: {exc}") from exc

    missing = sorted(_REQUIRED_TOP_LEVEL - set(result.keys()))
    if missing:
        raise RuntimeError(f"Location enrichment missing fields: {', '.join(missing)}")

    if (
        not isinstance(result.get("landmark_proximity"), list)
        or len(result["landmark_proximity"]) < 2
    ):
        raise RuntimeError("landmark_proximity must be a list with at least 2 items")
    if (
        not isinstance(result.get("best_trip_occasions"), list)
        or len(result["best_trip_occasions"]) < 2
    ):
        raise RuntimeError("best_trip_occasions must be a list with at least 2 items")

    log.info(
        "location_enrichment: done listing_id=%s headline=%r",
        listing_id,
        (result.get("location_summary") or {}).get("headline", "")[:80]
        if isinstance(result.get("location_summary"), dict)
        else "",
    )
    return result
