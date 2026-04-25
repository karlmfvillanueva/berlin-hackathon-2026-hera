"""LLM-based editorial classifier.

Sends listing summary to Claude and gets back structured AgentDecision fields
(vibes, hook, pacing, angle, background). Uses tool_use JSON output pattern —
more reliable than parsing free-text JSON.
"""

import os

import anthropic

from src.agent.models import Belief, ScrapedListing
from src.logger import log

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024
_TEMPERATURE = 0.4

# Tool schema that forces Claude to return structured editorial decisions
_TOOL_SCHEMA: dict = {
    "name": "editorial_decision",
    "description": (
        "Return a structured editorial decision for how to turn an Airbnb listing "
        "into a compelling 15-second vertical video. Every field must be a complete, "
        "opinionated sentence — not a placeholder."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vibes": {
                "type": "string",
                "description": (
                    "3-5 dot-separated vibe tags that define the visual and emotional "
                    "tone. e.g. 'minimalist · industrial · rooftop · golden hour'"
                ),
            },
            "hook": {
                "type": "string",
                "description": (
                    "One sentence: what to open the video with in the first 3 seconds "
                    "and why it's the strongest attribute of this listing."
                ),
            },
            "pacing": {
                "type": "string",
                "description": (
                    "One sentence: rough timeline structure for the 15s video. "
                    "e.g. 'Fast cuts 0-5s · hold on hero shot 5-10s · CTA 10-15s.'"
                ),
            },
            "angle": {
                "type": "string",
                "description": (
                    "One sentence: the editorial framing. What story is this video telling? "
                    "e.g. 'Lifestyle over feature list — sell the morning, not the mattress.'"
                ),
            },
            "background": {
                "type": "string",
                "description": (
                    "One sentence: how the reference images should work under motion graphics. "
                    "e.g. '6 hero images cross-fading under animated text overlays.'"
                ),
            },
            "beliefs_applied": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List the rule_key strings of every belief from the 'Your beliefs' "
                    "block above that influenced this decision. Empty list if none "
                    "applied or if no beliefs block was provided."
                ),
            },
        },
        "required": ["vibes", "hook", "pacing", "angle", "background"],
    },
}

_SYSTEM_PROMPT = """You are an editorial director for a short-form video agency.
Your job: read an Airbnb listing and decide how to turn it into a compelling 15-second vertical
video (9:16, 1080p) that earns the stop-scroll on Instagram Reels or TikTok.

You must be opinionated. Vague platitudes ("great listing!") are unacceptable.
Every decision must be specific to THIS listing — the strongest unique attribute, not the average.
You are making a creative call, not describing a template.

Think like a filmmaker pitching a commercial: what is the ONE thing that makes someone want to
stay here? Build everything around that one thing."""


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


def _build_system_prompt(beliefs: list[Belief]) -> str:
    """Phase 1 system prompt + Phase 2 'Your beliefs' block when beliefs are present."""
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


def classify(listing: ScrapedListing, beliefs: list[Belief] | None = None) -> dict:
    """Call Claude and return the raw tool input dict with editorial decisions.

    Returns a dict with keys: vibes, hook, pacing, angle, background, and
    optionally beliefs_applied (list[str] of rule_keys).
    Raises RuntimeError on any Anthropic API failure.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_HACKATHON_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)

    beliefs = beliefs or []
    log.info(
        "classifier: calling %s for listing=%s beliefs_injected=%d",
        _MODEL,
        listing.url,
        len(beliefs),
    )

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        system=_build_system_prompt(beliefs),
        tools=[_TOOL_SCHEMA],  # type: ignore[list-item]
        tool_choice={"type": "tool", "name": "editorial_decision"},
        messages=[{"role": "user", "content": _build_user_message(listing)}],
    )

    # With tool_choice forced, the first content block is always tool_use
    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if not tool_block:
        raise RuntimeError("Classifier returned no tool_use block")

    result: dict = tool_block.input  # type: ignore[union-attr]
    log.info(
        "classifier: done. vibes=%r hook=%r",
        result.get("vibes"),
        result.get("hook", "")[:80],
    )
    return result
