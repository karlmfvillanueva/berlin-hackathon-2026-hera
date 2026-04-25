"""Deterministic photo scorer.

Scores each photo against the agent's editorial decision (vibes + hook)
using keyword matching on the photo label. No LLM calls.
Returns top-5 photo URLs ordered by score descending.
"""

from src.agent.models import Photo

# Labels that indicate poor-fit or low-visual-impact photos
_NEGATIVE_LABELS = {"bathroom", "storage", "closet", "toilet", "laundry", "utility"}

# Labels that are universally strong visual signals
_POSITIVE_LABELS = {"view", "natural light", "rooftop", "terrace", "balcony", "skyline", "panorama"}


def _tokenise(text: str) -> set[str]:
    """Lower-case word tokens from a string."""
    return {w.strip("·.,;:-") for w in text.lower().split() if w}


def score_images(photos: list[Photo], vibes: str, hook: str) -> list[str]:
    """Score photos and return top-5 URLs.

    Scoring rules:
    - +1 per vibe tag token that appears in the photo label
    - +2 for universal strong signals (view, rooftop, natural light, terrace, balcony)
    - +2 if any hook keyword appears in the photo label
    - +1 for photos in position 0-2 (hosts front-load their best shots)
    - -1 for negative-signal labels (bathroom, storage, closet)
    """
    vibe_tokens = _tokenise(vibes)
    hook_tokens = _tokenise(hook)

    scored: list[tuple[int, int, str]] = []  # (score, original_index, url)

    for idx, photo in enumerate(photos):
        label_tokens = _tokenise(photo.label or "")
        score = 0

        # Vibe match
        score += len(vibe_tokens & label_tokens)

        # Universal strong signals
        if label_tokens & _POSITIVE_LABELS:
            score += 2

        # Hook keyword overlap
        if label_tokens & hook_tokens:
            score += 2

        # Position bonus — first 3 photos
        if idx < 3:
            score += 1

        # Penalty for low-value rooms
        if label_tokens & _NEGATIVE_LABELS:
            score -= 1

        scored.append((score, idx, photo.url))

    # Sort by score desc, then original index asc (stable tie-break preserves host ordering)
    scored.sort(key=lambda t: (-t[0], t[1]))

    return [url for _, _, url in scored[:5]]
