"""Orchestrates listing intelligence for one fixture listing.

run(listing) -> AgentDecision

Steps:
  1. Build a minimal scrape-shaped document from ``ScrapedListing`` (fixture shim).
  2. Run classify_icp + enrich_location + evaluate_reviews (parallel).
  3. Run derive_visual_system and analyse_photos in parallel (both need ICP + location + reviews).
  4. Run Final_Assembly (Strategic Opinion Agent) for the Hera prompt + reference URLs.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.agent.Final_Assembly import assemble_strategic_hera_prompt
from src.agent.ICP_Classifier import classify_icp
from src.agent.Location_Enrichment import enrich_location
from src.agent.Photo_Analyser import analyse_photos
from src.agent.Reviews_evaluation import evaluate_reviews
from src.agent.Visual_systems import derive_visual_system
from src.agent.models import AgentDecision, ScrapedListing
from src.logger import log


def _listing_to_scrape_document(listing: ScrapedListing) -> dict[str, Any]:
    """Shape fixture data like an Airbnb scrape JSON so ICP + Location agents can consume it."""
    return {
        "source": "scraped_listing_fixture_shim",
        "groups": {
            "core_identifiers": {
                "listing_id": "fixture-listing",
                "url_canonical": listing.url,
            },
        },
        "presentation": {
            "title": listing.title,
            "location_subtitle": listing.location,
            "price_per_night_display": listing.price_display,
            "bedrooms_bathrooms_sleeps_line": listing.bedrooms_sleeps,
            "description_plain": listing.description,
            "amenity_labels": listing.amenities,
            "photo_assets": [{"url": p.url, "alt_text": p.label or ""} for p in listing.photos],
            "review_tags": listing.review_tags,
            "review_quotes_verbatim": listing.review_quotes,
            "unavailable_amenities": listing.unavailable_amenities,
        },
    }


def run(listing: ScrapedListing) -> AgentDecision:
    """Run prerequisite listing agents + Final Assembly and return decision for API + Hera."""
    log.info("orchestrator: start listing=%s", listing.url)
    scrape = _listing_to_scrape_document(listing)

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_icp = pool.submit(classify_icp, scrape)
        fut_loc = pool.submit(enrich_location, scrape)
        fut_reviews = pool.submit(evaluate_reviews, scrape)
        icp = fut_icp.result()
        loc = fut_loc.result()
        reviews = fut_reviews.result()

    with ThreadPoolExecutor(max_workers=2) as pool2:
        fut_visual = pool2.submit(derive_visual_system, icp=icp, location_enrichment=loc)
        fut_photos = pool2.submit(analyse_photos, scrape, icp, loc, reviews)
        visual_system = fut_visual.result()
        photo_analysis = fut_photos.result()

    hera_prompt, selected = assemble_strategic_hera_prompt(
        listing=listing,
        icp=icp,
        location_enrichment=loc,
        reviews_evaluation=reviews,
        visual_system=visual_system,
        photo_analysis=photo_analysis,
    )

    decision = AgentDecision(
        icp=icp,
        location_enrichment=loc,
        reviews_evaluation=reviews,
        visual_system=visual_system,
        photo_analysis=photo_analysis,
        hera_prompt=hera_prompt,
        duration_seconds=15,
        selected_image_urls=selected,
    )

    best = icp.get("best_icp") if isinstance(icp.get("best_icp"), dict) else {}
    log.info(
        "orchestrator: done icp=%r loc_headline_chars=%d reviews_quotes=%d visual_setting=%r "
        "photo_shortlist=%d prompt_chars=%d images=%d",
        best.get("persona"),
        len(str((loc.get("location_summary") or {}).get("headline", ""))),
        len(reviews.get("best_video_quotes") or []) if isinstance(reviews, dict) else 0,
        visual_system.get("inferred_setting") if isinstance(visual_system, dict) else None,
        len(photo_analysis.get("selected_indices_hero_first") or [])
        if isinstance(photo_analysis, dict)
        else 0,
        len(hera_prompt),
        len(selected),
    )
    return decision
