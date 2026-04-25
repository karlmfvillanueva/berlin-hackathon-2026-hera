# ruff: noqa: E501
"""Reviews Evaluation agent for Airbnb scrape JSON.

Consumes the raw scrape document (see architecture airbnb-scrape schema / template;
e.g. ``groups.ratings_and_reviews``, ``presentation.review_quotes_verbatim``)
and returns conversion-focused review proof as structured JSON via Gemini structured
output (response_schema).

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

_MODEL = os.getenv("GEMINI_REVIEWS_EVALUATION_MODEL", "gemini-2.5-pro")
# 2.5-Pro is a reasoning model: max_output_tokens covers thinking + JSON response.
_MAX_OUTPUT_TOKENS = 12800
_THINKING_BUDGET = 2048
_TEMPERATURE = 0.25

_FREQ = {"type": "string", "enum": ["low", "medium", "high"]}
_CONV = {"type": "string", "enum": ["low", "medium", "high"]}
_RISK = {"type": "string", "enum": ["low", "medium", "high"]}
_MOBILE = {"type": "string", "enum": ["high", "medium", "low"]}
_SCENE = {
    "type": "string",
    "enum": [
        "hook",
        "location proof",
        "social proof",
        "feature payoff",
        "emotional climax",
        "CTA support",
    ],
}
_CLAIM_SOURCE = {
    "type": "string",
    "enum": ["guest_review", "listing_fact", "host_claim_only", "unsupported"],
}

_QUOTE_ITEM = {
    "type": "object",
    "properties": {
        "quote": {"type": "string"},
        "guest_first_name": {"type": "string"},
        "month": {"type": "string"},
        "year": {"type": "string"},
    },
    "required": ["quote", "guest_first_name", "month", "year"],
}

_SYSTEM_PROMPT = """You are the Reviews Evaluation Agent for short-term rental video generation.

Your job is NOT to summarize all reviews.

Your job is to extract conversion-relevant guest proof.

You identify what real guests repeatedly praise, what they complain about, and which exact review quotes can be safely used in the video.

Reviews are stronger than host claims.

But only if they are:

- specific
- emotional
- relevant to the chosen guest type
- usable as social proof
- verbatim

YOUR TASK

You must:

1. Extract repeated positive patterns from reviews
2. Extract repeated negative patterns from reviews
3. Identify exact verbatim quotes suitable for video
4. Separate guest-backed claims from host-only claims
5. Flag risky or unusable quotes
6. Recommend which review themes are strongest for conversion

Do NOT invent quotes.

Do NOT rewrite quotes.

Do NOT clean up grammar.

Do NOT turn host copy into guest voice.

Only use exact guest wording from review comment text in the scrape. If a scrape field is host-written (listing title, description, amenity marketing copy), never treat it as a guest quote.

WHAT MAKES A GOOD VIDEO QUOTE

Good quote:

- short
- emotional
- specific
- credible
- tied to a strong selling point
- easy to read on mobile

Bad quote:

- too long
- vague
- purely logistical
- full of irrelevant detail
- mentions weak points
- requires context

CLAIM SAFETY RULES

A claim can be used in the video only if:

1. It appears in guest review text, OR
2. It appears in verified listing facts (structured amenities, capacity, location labels from the scrape — not subjective host adjectives)

If a phrase comes only from host marketing copy, label it as host_claim_only with allowed_in_video false.

Never present host claims as guest experience.

NEGATIVE REVIEW RULES

Do not include negative reviews in the video.

But you must extract them for strategy under negative_patterns and creative_implications.what_to_hide_or_avoid.

They help decide what to hide or avoid (noise, shared bathroom, stairs, small room, weak AC, parking, neighbor view, sofa bed, etc.).

QUALITY BAR

This should feel like a performance marketer mining reviews for conversion proof.

Not a generic review summary.

Be strict. Be evidence-based. Protect truth.

Output strict structured JSON matching the response schema, no preamble."""

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "review_summary": {
            "type": "object",
            "properties": {
                "overall_sentiment": {"type": "string"},
                "review_count_used": {"type": "integer"},
                "most_repeated_positive_theme": {"type": "string"},
                "most_repeated_negative_theme": {"type": "string"},
            },
            "required": [
                "overall_sentiment",
                "review_count_used",
                "most_repeated_positive_theme",
                "most_repeated_negative_theme",
            ],
        },
        "positive_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "frequency": _FREQ,
                    "guest_value": {"type": "string"},
                    "conversion_value": _CONV,
                    "supporting_quotes": {"type": "array", "items": _QUOTE_ITEM},
                },
                "required": [
                    "theme",
                    "frequency",
                    "guest_value",
                    "conversion_value",
                    "supporting_quotes",
                ],
            },
        },
        "negative_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "frequency": _FREQ,
                    "risk_level": _RISK,
                    "strategy_implication": {"type": "string"},
                    "supporting_quotes": {"type": "array", "items": _QUOTE_ITEM},
                },
                "required": [
                    "theme",
                    "frequency",
                    "risk_level",
                    "strategy_implication",
                    "supporting_quotes",
                ],
            },
        },
        "best_video_quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "guest_first_name": {"type": "string"},
                    "month": {"type": "string"},
                    "year": {"type": "string"},
                    "theme": {"type": "string"},
                    "best_scene_use": _SCENE,
                    "why_it_works": {"type": "string"},
                    "mobile_readability": _MOBILE,
                },
                "required": [
                    "quote",
                    "guest_first_name",
                    "month",
                    "year",
                    "theme",
                    "best_scene_use",
                    "why_it_works",
                    "mobile_readability",
                ],
            },
        },
        "claims_validation": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "source": _CLAIM_SOURCE,
                    "allowed_in_video": {"type": "boolean"},
                    "notes": {"type": "string"},
                },
                "required": ["claim", "source", "allowed_in_video", "notes"],
            },
        },
        "quotes_to_avoid": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["quote", "reason"],
            },
        },
        "creative_implications": {
            "type": "object",
            "properties": {
                "what_reviews_prove": {"type": "array", "items": {"type": "string"}},
                "what_to_emphasize": {"type": "array", "items": {"type": "string"}},
                "what_to_hide_or_avoid": {"type": "array", "items": {"type": "string"}},
                "strongest_review_backed_angle": {"type": "string"},
            },
            "required": [
                "what_reviews_prove",
                "what_to_emphasize",
                "what_to_hide_or_avoid",
                "strongest_review_backed_angle",
            ],
        },
    },
    "required": [
        "review_summary",
        "positive_patterns",
        "negative_patterns",
        "best_video_quotes",
        "claims_validation",
        "quotes_to_avoid",
        "creative_implications",
    ],
}

_REQUIRED_TOP_LEVEL = frozenset(_RESPONSE_SCHEMA["required"])


def _build_user_message(scrape: Mapping[str, Any]) -> str:
    payload = json.dumps(scrape, ensure_ascii=False, separators=(",", ":"))
    return (
        "INPUT: JSON-structured Airbnb listing scrape (full document).\n"
        "Mine reviews from ratings_and_reviews (reviews_inline_sample, reviews_full_corpus, "
        "review_tags_ai, category_ratings) and any presentation fields that contain verbatim guest "
        "quotes. Use listing description/title only for claims_validation (host vs guest), "
        "never as guest quotes.\n"
        "If there are no guest reviews, return empty arrays where appropriate, set "
        "review_count_used to 0, explain in review_summary.overall_sentiment, and still run "
        "claims_validation on notable host phrases as host_claim_only where applicable.\n\n"
        f"{payload}"
    )


def _assert_freq(val: Any, ctx: str) -> None:
    if val not in ("low", "medium", "high"):
        raise RuntimeError(f"{ctx}: frequency/risk must be low|medium|high, got {val!r}")


def _validate_result(result: dict[str, Any]) -> None:
    missing = sorted(_REQUIRED_TOP_LEVEL - set(result.keys()))
    if missing:
        raise RuntimeError(f"reviews_evaluation missing top-level keys: {', '.join(missing)}")

    rs = result.get("review_summary")
    if not isinstance(rs, dict):
        raise RuntimeError("review_summary must be an object")
    for key in (
        "overall_sentiment",
        "review_count_used",
        "most_repeated_positive_theme",
        "most_repeated_negative_theme",
    ):
        if key == "review_count_used":
            if not isinstance(rs.get(key), int) or rs[key] < 0:
                raise RuntimeError("review_summary.review_count_used must be a non-negative int")
        elif not isinstance(rs.get(key), str):
            raise RuntimeError(f"review_summary.{key} must be a string")

    for label, key in (
        ("positive_patterns", "positive_patterns"),
        ("negative_patterns", "negative_patterns"),
        ("best_video_quotes", "best_video_quotes"),
        ("claims_validation", "claims_validation"),
        ("quotes_to_avoid", "quotes_to_avoid"),
    ):
        arr = result.get(key)
        if not isinstance(arr, list):
            raise RuntimeError(f"{label} must be an array")

    for i, p in enumerate(result["positive_patterns"]):  # type: ignore[arg-type]
        if not isinstance(p, dict):
            raise RuntimeError(f"positive_patterns[{i}] must be an object")
        _assert_freq(p.get("frequency"), f"positive_patterns[{i}]")
        if p.get("conversion_value") not in ("low", "medium", "high"):
            raise RuntimeError(f"positive_patterns[{i}].conversion_value invalid")
        sq = p.get("supporting_quotes")
        if not isinstance(sq, list):
            raise RuntimeError(f"positive_patterns[{i}].supporting_quotes must be an array")

    for i, p in enumerate(result["negative_patterns"]):  # type: ignore[arg-type]
        if not isinstance(p, dict):
            raise RuntimeError(f"negative_patterns[{i}] must be an object")
        _assert_freq(p.get("frequency"), f"negative_patterns[{i}]")
        _assert_freq(p.get("risk_level"), f"negative_patterns[{i}].risk_level")
        sq = p.get("supporting_quotes")
        if not isinstance(sq, list):
            raise RuntimeError(f"negative_patterns[{i}].supporting_quotes must be an array")

    allowed_scenes = frozenset(
        {
            "hook",
            "location proof",
            "social proof",
            "feature payoff",
            "emotional climax",
            "CTA support",
        }
    )
    for i, q in enumerate(result["best_video_quotes"]):  # type: ignore[arg-type]
        if not isinstance(q, dict):
            raise RuntimeError(f"best_video_quotes[{i}] must be an object")
        if q.get("best_scene_use") not in allowed_scenes:
            raise RuntimeError(f"best_video_quotes[{i}].best_scene_use invalid")
        if q.get("mobile_readability") not in ("high", "medium", "low"):
            raise RuntimeError(f"best_video_quotes[{i}].mobile_readability invalid")

    allowed_sources = frozenset({"guest_review", "listing_fact", "host_claim_only", "unsupported"})
    for i, c in enumerate(result["claims_validation"]):  # type: ignore[arg-type]
        if not isinstance(c, dict):
            raise RuntimeError(f"claims_validation[{i}] must be an object")
        if c.get("source") not in allowed_sources:
            raise RuntimeError(f"claims_validation[{i}].source invalid")
        if not isinstance(c.get("allowed_in_video"), bool):
            raise RuntimeError(f"claims_validation[{i}].allowed_in_video must be boolean")

    ci = result.get("creative_implications")
    if not isinstance(ci, dict):
        raise RuntimeError("creative_implications must be an object")
    for arr_key in ("what_reviews_prove", "what_to_emphasize", "what_to_hide_or_avoid"):
        if not isinstance(ci.get(arr_key), list):
            raise RuntimeError(f"creative_implications.{arr_key} must be an array")
    if not isinstance(ci.get("strongest_review_backed_angle"), str):
        raise RuntimeError("creative_implications.strongest_review_backed_angle must be a string")


def evaluate_reviews(scrape: Mapping[str, Any]) -> dict[str, Any]:
    """Run the Reviews Evaluation Agent on an Airbnb scrape dict.

    Returns a dict matching the reviews_evaluation contract (review_summary,
    positive_patterns, negative_patterns, best_video_quotes, claims_validation,
    quotes_to_avoid, creative_implications).

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

    log.info("reviews_evaluation: calling %s listing_id=%s", _MODEL, listing_id)

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
        raise RuntimeError("reviews_evaluation: Gemini returned empty response")

    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"reviews_evaluation: invalid JSON from Gemini: {exc}") from exc

    _validate_result(result)

    n_best = len(result.get("best_video_quotes") or [])
    log.info("reviews_evaluation: done listing_id=%s best_video_quotes=%d", listing_id, n_best)
    return result
