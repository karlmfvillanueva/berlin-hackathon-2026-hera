"""Builds the final Hera prompt string from listing + agent decision fields.

The prompt tells Hera exactly what to render: format, structure, tone, imagery.
Capped at 1500 chars to stay well within any undocumented Hera limits.
"""

from src.agent.models import AgentDecision, ScrapedListing

_PROMPT_TEMPLATE = """\
Create a 15-second vertical video (9:16, 1080p) for an Airbnb listing.

LISTING: {title} — {location}
VIBES: {vibes}

HOOK (0-3s): {hook}
PACING: {pacing}
ANGLE: {angle}
VISUAL APPROACH: {background}

REFERENCE IMAGES provided show key spaces of this listing. Use them as the visual backbone \
— cross-fade between them under animated text and motion graphics. Prioritise photos of \
{photo_labels}.

TONE: aspirational but specific. The audience scrolling past should feel the listing \
before they read a word. No stock-photo aesthetics. No generic travel montage. \
This is {location} — make it feel like it.

END CARD (13-15s): Show the listing title and "{price}/night" in clean typography.
"""

_MAX_CHARS = 1500


def build_prompt(listing: ScrapedListing, decision: AgentDecision) -> str:
    """Return a Hera-ready prompt string, trimmed to _MAX_CHARS."""
    # Build a short label summary from the top selected images
    selected_labels = []
    selected_urls_set = set(decision.selected_image_urls)
    for photo in listing.photos:
        if photo.url in selected_urls_set and photo.label:
            selected_labels.append(photo.label.split("—")[0].strip())

    photo_labels = ", ".join(selected_labels[:4]) if selected_labels else "the key spaces"

    prompt = _PROMPT_TEMPLATE.format(
        title=listing.title,
        location=listing.location,
        vibes=decision.vibes,
        hook=decision.hook,
        pacing=decision.pacing,
        angle=decision.angle,
        background=decision.background,
        photo_labels=photo_labels,
        price=listing.price_display,
    )

    # Hard truncate with a note if somehow over limit
    if len(prompt) > _MAX_CHARS:
        prompt = prompt[: _MAX_CHARS - 3] + "..."

    return prompt
