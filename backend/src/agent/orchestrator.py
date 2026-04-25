"""Orchestrates the full agent pipeline for one listing.

run(listing, outpaint_enabled=False) -> AgentDecision

Steps:
  1. classify — LLM call, returns editorial decisions (vibes/hook/pacing/angle/background)
  2. score_images — deterministic, picks top-5 reference photos
  3. outpaint_5_photos — async, only when outpaint_enabled (B-03)
  4. build_prompt — fills the Hera prompt template
"""

from src.agent.beliefs import fetch_beliefs
from src.agent.classifier import classify
from src.agent.image_scorer import score_images
from src.agent.models import AgentDecision, ScrapedListing
from src.agent.outpainter import outpaint_5_photos
from src.agent.prompt_builder import build_prompt
from src.logger import log


async def run(listing: ScrapedListing, outpaint_enabled: bool = False) -> AgentDecision:
    """Run the full agent pipeline and return a populated AgentDecision."""
    log.info("orchestrator: start listing=%s outpaint=%s", listing.url, outpaint_enabled)

    beliefs = fetch_beliefs(limit=10)
    raw = classify(listing, beliefs=beliefs)
    beliefs_applied = raw.get("beliefs_applied", []) or []
    log.info(
        "classifier: beliefs_injected=%d beliefs_applied=%d",
        len(beliefs),
        len(beliefs_applied),
    )

    decision = AgentDecision(
        vibes=raw["vibes"],
        hook=raw["hook"],
        pacing=raw["pacing"],
        angle=raw["angle"],
        background=raw["background"],
        selected_image_urls=[],
        hera_prompt="",
        outpaint_enabled=outpaint_enabled,
        beliefs_applied=beliefs_applied,
    )

    decision.selected_image_urls = score_images(listing.photos, decision.vibes, decision.hook)

    if outpaint_enabled:
        decision.selected_image_urls = await outpaint_5_photos(decision.selected_image_urls)

    decision.hera_prompt = build_prompt(listing, decision)

    log.info(
        "orchestrator: done. images=%d prompt_chars=%d",
        len(decision.selected_image_urls),
        len(decision.hera_prompt),
    )
    return decision
