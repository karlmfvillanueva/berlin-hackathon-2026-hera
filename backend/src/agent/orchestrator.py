"""Orchestrates the full agent pipeline for one listing.

run(listing) -> AgentDecision

Steps:
  1. classify — LLM call, returns editorial decisions (vibes/hook/pacing/angle/background)
  2. score_images — deterministic, picks top-5 reference photos
  3. build_prompt — fills the Hera prompt template
"""

from src.agent.classifier import classify
from src.agent.image_scorer import score_images
from src.agent.models import AgentDecision, ScrapedListing
from src.agent.prompt_builder import build_prompt
from src.logger import log


def run(listing: ScrapedListing) -> AgentDecision:
    """Run the full agent pipeline and return a populated AgentDecision."""
    log.info("orchestrator: start listing=%s", listing.url)

    raw = classify(listing)
    decision = AgentDecision(
        vibes=raw["vibes"],
        hook=raw["hook"],
        pacing=raw["pacing"],
        angle=raw["angle"],
        background=raw["background"],
        selected_image_urls=[],
        hera_prompt="",
    )

    decision.selected_image_urls = score_images(listing.photos, decision.vibes, decision.hook)
    decision.hera_prompt = build_prompt(listing, decision)

    log.info(
        "orchestrator: done. images=%d prompt_chars=%d",
        len(decision.selected_image_urls),
        len(decision.hera_prompt),
    )
    return decision
