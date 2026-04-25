"""Pydantic models for the agent layer. All data shapes live here."""

from typing import Any

from pydantic import BaseModel, Field


class Photo(BaseModel):
    url: str
    label: str | None = None  # alt text or filename hint


class ScrapedListing(BaseModel):
    url: str
    title: str
    description: str
    amenities: list[str]
    photos: list[Photo]
    location: str
    price_display: str
    bedrooms_sleeps: str  # e.g. "2 BR · sleeps 4 · 1 bath"
    person_capacity: int | None = None
    rating_overall: float | None = None
    reviews_count: int | None = None
    review_tags: list[str] = Field(default_factory=list)
    review_quotes: list[str] = Field(default_factory=list)
    unavailable_amenities: list[str] = Field(default_factory=list)


class AgentDecision(BaseModel):
    """Listing intelligence + Hera submission bridge.

    ``icp`` / ``location_enrichment`` / ``reviews_evaluation`` / ``visual_system`` /
    ``photo_analysis`` are structured outputs from the prerequisite listing agents.
    ``hera_prompt`` is produced by ``Final_Assembly.assemble_strategic_hera_prompt``
    (Strategic Opinion Agent) from those outputs plus the Photo Analyser shortlist
    and listing summary.
    """

    icp: dict[str, Any]
    location_enrichment: dict[str, Any]
    reviews_evaluation: dict[str, Any]
    visual_system: dict[str, Any]
    photo_analysis: dict[str, Any]
    duration_seconds: int = 15
    selected_image_urls: list[str] = Field(default_factory=list)
    hera_prompt: str


class ListingResponse(BaseModel):
    listing: ScrapedListing
    decision: AgentDecision


class GenerateRequest(BaseModel):
    listing_url: str
    listing: ScrapedListing
    decision: AgentDecision


class GenerateResponse(BaseModel):
    video_id: str
    decision: AgentDecision
