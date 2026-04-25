# ruff: noqa: E501
"""Visual direction agent for short-form property listing videos (TikTok).

Consumes structured outputs from ``ICP_Classifier`` (``classify_icp``) and
``Location_Enrichment`` (``enrich_location``) and returns an art-directed
visual system spec via Gemini structured output (response_schema).

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

from src.agent.icp_classifier import ALLOWED_PERSONAS
from src.logger import log

_MODEL = os.getenv("GEMINI_VISUAL_SYSTEMS_MODEL", "gemini-2.5-pro")
# 2.5-Pro is a reasoning model: max_output_tokens covers thinking + JSON response.
_MAX_OUTPUT_TOKENS = 4400
_THINKING_BUDGET = 2048
_TEMPERATURE = 0.45

_SETTING_LABELS: tuple[str, ...] = (
    "city",
    "coastal",
    "mountain",
    "countryside",
    "desert",
)

_SYSTEM_PROMPT = """You are the visual direction agent for short-form property listing videos on TikTok.

You receive two inputs embedded in the user message as JSON:
- TARGET: the guest profile — exactly one of these labels (from ICP best_icp.persona):
  Friend group celebration | Party group | Couples weekend break | Solo traveler |
  Digital nomad | First-time city tourist | Budget-smart traveler | Luxury experience seeker |
  Family visiting adult child
- LOCATION CONTEXT: the full location_enrichment object from another agent. Infer the property
  setting as ONE of: city, coastal, mountain, countryside, desert. Base inference on headlines,
  neighborhood identity, landmarks, and trip occasions — not guesswork unrelated to the JSON.

Based on TARGET + inferred setting, output one visual system spec. Every tool field must be
filled with specific, intentional choices (hex codes where required + a short mood label in the
same string). No generic filler like "modern and clean" without concrete creative choices.

OUTPUT SEMANTICS (each string must read like professional art direction):
- primary_background: dominant colour for most scenes — include #RRGGBB and a mood label.
- cta_card_only: distinct colour used ONLY on the final CTA card — #RRGGBB + mood label.
- primary_type: main on-screen overlay text colour — #RRGGBB + mood label.
- accent: highlight for key words, underlines, motion accents — #RRGGBB + mood label.
- font_review_quotes: describe type style for guest review quotes (e.g. thin italic serif).
- font_labels_stats_ctas: describe type for labels, stats, CTAs (e.g. geometric sans, lowercase).
- pacing: rhythm with approximate timings (e.g. ~1s hard cuts vs ~2.5s dissolves).
- transitions: named transition style matched to target energy + setting.
- music: genre + approximate BPM + mood adjectives.

LOGIC RULES

TARGET shapes: tone, palette temperature, font personality, pacing energy.
LOCATION (inferred setting) shapes: specific hues, texture references, transition style, music genre.

Palette + tone guide per target:
- Friend group celebration → warm social: golden yellow, burnt orange, off-white; medium-fast;
  indie pop or feel-good funk energy in music description.
- Party group → high contrast nightlife: near-black, electric pink, gold; fast; hard cuts / flash
  frames; house or tech-house energy.
- Couples weekend break → warm desaturated intimacy: terracotta, dusty rose, amber, burgundy;
  slow; soft dissolves; lo-fi acoustic or ambient music mood.
- Solo traveler → contemplative: slate blue, warm grey, muted forest; medium; slow zoom-ins;
  ambient electronic or soft indie mood.
- Digital nomad → editorial cool-neutral: concrete white, slate, forest green; medium; clean
  horizontal slides; minimal electronic or focus ambient mood.
- First-time city tourist → bright curious: cobalt, warm white, sunflower yellow; medium-fast;
  dynamic pans; upbeat acoustic or light pop mood.
- Budget-smart traveler → honest warm: mustard, warm off-white, rust; straightforward clean cuts;
  lo-fi hip hop or cheerful acoustic mood.
- Luxury experience seeker → restrained aspirational: deep champagne, black, aged gold, ivory;
  very slow; cinematic wipes or slow push-ins; minimal jazz or orchestral ambient mood.
- Family visiting adult child → warm nostalgic safe: soft terracotta, cream, sage; slow gentle;
  cross-dissolves; light acoustic or gentle folk mood.

Location modifier (layer on top of target palette — adjust hues/texture/pacing/music, not the
target's core emotional register):
- city → more contrast, sharper transitions, slightly faster pacing, urban texture language.
- coastal → sandy neutrals or soft blues in hues, dreamier transitions.
- mountain → deep greens and slate in hues, slower feel, cinematic wide-shot language.
- countryside → ochre and linen tones, gentler pacing, acoustic-leaning music wording.
- desert → burnt sienna, dusty gold, sparse minimal feel, haze-type transitions.

Conflict rule: If target and setting feel mismatched (e.g. Party group + countryside), keep TARGET
energy for mood and pacing; soften only with LOCATION palette and texture. Never flip the target
into a different emotional register.

Output strict structured JSON matching the response schema, no preamble."""


_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "inferred_setting": {
            "type": "string",
            "description": "One of: city, coastal, mountain, countryside, desert — inferred from location JSON.",
            "enum": list(_SETTING_LABELS),
        },
        "primary_background": {
            "type": "string",
            "description": "Dominant scene background: #hex + mood label.",
        },
        "cta_card_only": {
            "type": "string",
            "description": "Final CTA card only: #hex + mood label, distinct from primary_background.",
        },
        "primary_type": {
            "type": "string",
            "description": "Main overlay text: #hex + mood label.",
        },
        "accent": {
            "type": "string",
            "description": "Highlights / motion accents: #hex + mood label.",
        },
        "font_review_quotes": {
            "type": "string",
            "description": "Type style for verbatim guest review quotes.",
        },
        "font_labels_stats_ctas": {
            "type": "string",
            "description": "Type style for labels, stats, and CTA typography.",
        },
        "pacing": {
            "type": "string",
            "description": "Edit rhythm with indicative scene lengths.",
        },
        "transitions": {
            "type": "string",
            "description": "Named transition vocabulary matching energy + setting.",
        },
        "music": {
            "type": "string",
            "description": "Genre + tempo (bpm) + mood — concrete, not vague.",
        },
    },
    "required": [
        "inferred_setting",
        "primary_background",
        "cta_card_only",
        "primary_type",
        "accent",
        "font_review_quotes",
        "font_labels_stats_ctas",
        "pacing",
        "transitions",
        "music",
    ],
}

_REQUIRED_FIELDS = frozenset(_RESPONSE_SCHEMA["required"])  # type: ignore[arg-type]


def _build_user_message(
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
) -> str:
    best = icp.get("best_icp") if isinstance(icp.get("best_icp"), dict) else {}
    persona = best.get("persona")
    persona_str = persona if isinstance(persona, str) else ""
    payload = {
        "TARGET_PERSONA": persona_str,
        "ALLOWED_TARGET_LABELS": list(ALLOWED_PERSONAS),
        "location_enrichment": location_enrichment,
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "Infer LOCATION SETTING (city | coastal | mountain | countryside | desert) from "
        "location_enrichment. Art-direct the visual system for TARGET_PERSONA + that setting.\n\n"
        f"{body}"
    )


def _hex_like_fragment(s: str) -> bool:
    u = s.upper()
    for i in range(len(u) - 6):
        window = u[i : i + 7]
        if (
            len(window) == 7
            and window[0] == "#"
            and all(c in "0123456789ABCDEF" for c in window[1:])
        ):
            return True
    return False


def _validate_visual_result(result: dict[str, Any]) -> None:
    missing = sorted(_REQUIRED_FIELDS - set(result.keys()))
    if missing:
        raise RuntimeError(f"visual_system missing fields: {', '.join(missing)}")

    setting = result.get("inferred_setting")
    if not isinstance(setting, str) or setting not in _SETTING_LABELS:
        raise RuntimeError(f"inferred_setting must be one of: {', '.join(_SETTING_LABELS)}")

    colour_fields = ("primary_background", "cta_card_only", "primary_type", "accent")
    for key in colour_fields:
        val = result.get(key)
        if not isinstance(val, str) or len(val.strip()) < 12:
            raise RuntimeError(f"{key} must be a substantive string with hex + mood")
        if not _hex_like_fragment(val):
            raise RuntimeError(f"{key} must include a #RRGGBB hex token")

    for key in (
        "font_review_quotes",
        "font_labels_stats_ctas",
        "pacing",
        "transitions",
        "music",
    ):
        val = result.get(key)
        if not isinstance(val, str) or len(val.strip()) < 8:
            raise RuntimeError(f"{key} must be a non-trivial string")


def derive_visual_system(
    icp: Mapping[str, Any],
    location_enrichment: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the Visual Systems agent on ICP + location enrichment dicts.

    Returns structured keys aligned with the response schema (including ``inferred_setting``).
    Raises ``RuntimeError`` if the API fails or validation fails.
    """
    project = os.getenv("GCP_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    if not project:
        raise RuntimeError("GCP_PROJECT is not set")

    best = icp.get("best_icp") if isinstance(icp.get("best_icp"), dict) else {}
    persona = best.get("persona")
    if not isinstance(persona, str) or persona not in ALLOWED_PERSONAS:
        raise RuntimeError("icp.best_icp.persona must be a valid allowed ICP label")

    log.info("visual_systems: calling %s persona=%r", _MODEL, persona)

    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model=_MODEL,
        contents=_build_user_message(icp, location_enrichment),
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
        raise RuntimeError("visual_systems: Gemini returned empty response")
    try:
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"visual_systems: invalid JSON from Gemini: {exc}") from exc

    _validate_visual_result(result)

    log.info(
        "visual_systems: done persona=%r setting=%r",
        persona,
        result.get("inferred_setting"),
    )
    return result


def format_visual_system_spec(spec: Mapping[str, Any]) -> str:
    """Render the spec as the human-readable block (labelled lines, exact OUTPUT FORMAT)."""
    return "\n".join(
        [
            f"Primary background: {spec.get('primary_background', '')}",
            f"CTA card only: {spec.get('cta_card_only', '')}",
            f"Primary type: {spec.get('primary_type', '')}",
            f"Accent: {spec.get('accent', '')}",
            f"Font type for guest review quotes: {spec.get('font_review_quotes', '')}",
            f"Font type for labels, stats, CTAs: {spec.get('font_labels_stats_ctas', '')}",
            f"Pacing: {spec.get('pacing', '')}",
            f"Transitions: {spec.get('transitions', '')}",
            f"Music: {spec.get('music', '')}",
        ]
    )
