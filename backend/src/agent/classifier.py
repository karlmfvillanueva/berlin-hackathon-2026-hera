"""LLM-based editorial classifier.

Sends listing summary to Gemini and gets back structured AgentDecision fields
(vibes, hook, pacing, angle, background) plus the beliefs that influenced the
decision. Uses Gemini's native JSON-schema mode (response_mime_type +
response_schema) — no tool-use boilerplate, the SDK returns a parsed Pydantic
model on response.parsed.
"""

import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.agent.models import Belief, ScrapedListing
from src.logger import log

_MODEL = "gemini-3.1-pro-preview"
_MAX_OUTPUT_TOKENS = 1024
_TEMPERATURE = 0.4


class EditorialDecisionSchema(BaseModel):
    """Structured output the model must return. Field descriptions are sent to
    Gemini as schema descriptions and steer the per-field generation."""

    vibes: str = Field(
        ...,
        description=(
            "3-5 dot-separated vibe tags that define the visual and emotional "
            "tone. e.g. 'minimalist · industrial · rooftop · golden hour'"
        ),
    )
    hook: str = Field(
        ...,
        description=(
            "One sentence: what to open the video with in the first 3 seconds "
            "and why it's the strongest attribute of this listing."
        ),
    )
    pacing: str = Field(
        ...,
        description=(
            "One sentence: rough timeline structure for the 15s video. "
            "e.g. 'Fast cuts 0-5s · hold on hero shot 5-10s · CTA 10-15s.'"
        ),
    )
    angle: str = Field(
        ...,
        description=(
            "One sentence: the editorial framing. What story is this video telling? "
            "e.g. 'Lifestyle over feature list — sell the morning, not the mattress.'"
        ),
    )
    background: str = Field(
        ...,
        description=(
            "One sentence: how the reference images should work under motion graphics. "
            "e.g. '6 hero images cross-fading under animated text overlays.'"
        ),
    )
    beliefs_applied: list[str] = Field(
        default_factory=list,
        description=(
            "rule_key strings of every belief from the 'Your beliefs' block that "
            "influenced this decision. Empty list if no beliefs block was provided "
            "or none applied."
        ),
    )


_SYSTEM_PROMPT = """You are an editorial director for a short-form video agency.
Your job: read an Airbnb listing and decide how to turn it into a compelling 15-second vertical
video (9:16, 1080p) that earns the stop-scroll on Instagram Reels or TikTok.

You must be opinionated. Vague platitudes ("great listing!") are unacceptable.
Every decision must be specific to THIS listing — the strongest unique attribute, not the average.
You are making a creative call, not describing a template.

Think like a filmmaker pitching a commercial: what is the ONE thing that makes someone want to
stay here? Build everything around that one thing."""


def _build_system_prompt(beliefs: list[Belief]) -> str:
    """Phase 1 base prompt + Phase 2 'Your beliefs' block when beliefs are present."""
    if not beliefs:
        return _SYSTEM_PROMPT
    beliefs_block = "\n".join(
        f"- {b.rule_key} (confidence {b.confidence:.2f}): {b.rule_text}" for b in beliefs
    )
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        "## Your beliefs (from real performance data)\n\n"
        "Apply these when relevant. Higher confidence = stronger influence. "
        "Always log which rule_keys you applied in beliefs_applied.\n\n"
        f"{beliefs_block}"
    )


def _build_user_message(listing: ScrapedListing) -> str:
    photo_labels = "\n".join(f"  - {p.label or 'unlabelled'}" for p in listing.photos)
    return f"""Listing: {listing.title}
Location: {listing.location}
Bedrooms/sleeps: {listing.bedrooms_sleeps}
Price: {listing.price_display}/night
Amenities: {", ".join(listing.amenities)}

Description:
{listing.description}

Photos (in order, hosts front-load their best shots):
{photo_labels}

Make your editorial decision for a 15-second 9:16 vertical video. Be specific to this listing."""


def classify(listing: ScrapedListing, beliefs: list[Belief] | None = None) -> dict:
    """Call Gemini and return the editorial decision dict.

    Returns a dict with keys: vibes, hook, pacing, angle, background, beliefs_applied.
    Raises RuntimeError on missing key or on a malformed/empty response.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    beliefs = beliefs or []
    log.info(
        "classifier: calling %s for listing=%s beliefs_injected=%d",
        _MODEL,
        listing.url,
        len(beliefs),
    )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=_MODEL,
        contents=_build_user_message(listing),
        config=types.GenerateContentConfig(
            system_instruction=_build_system_prompt(beliefs),
            response_mime_type="application/json",
            response_schema=EditorialDecisionSchema,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
        ),
    )

    parsed = response.parsed
    if not isinstance(parsed, EditorialDecisionSchema):
        raise RuntimeError(f"Gemini returned no parseable schema. raw={response.text[:200]}")

    log.info(
        "classifier: done. vibes=%r hook=%r",
        parsed.vibes,
        parsed.hook[:80],
    )
    return parsed.model_dump()
