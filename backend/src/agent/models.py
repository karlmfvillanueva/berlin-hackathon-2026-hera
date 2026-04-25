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
    # Optional Phase 3 fields. Populated by richer scrapers when present and consumed by the
    # multi-agent pipeline shim that reshapes ScrapedListing into a scrape-document for the
    # ICP / Location / Reviews / Photo agents. Falsy / empty defaults keep the simpler scraper
    # path working unchanged.
    person_capacity: int | None = None
    rating_overall: float | None = None
    reviews_count: int | None = None
    review_tags: list[str] = Field(default_factory=list)
    review_quotes: list[str] = Field(default_factory=list)
    unavailable_amenities: list[str] = Field(default_factory=list)


class AgentDecision(BaseModel):
    vibes: str  # e.g. "minimalist · industrial · greenery · rooftop"
    hook: str  # 1 sentence — opening seconds, strongest attribute
    pacing: str  # 1 sentence — rough timeline structure
    angle: str  # 1 sentence — editorial framing
    background: str  # 1 sentence — image composition / motion graphics approach
    selected_image_urls: list[str]  # top 5 ranked, max 5
    hera_prompt: str  # final prompt sent to Hera
    # Phase 2 additive
    outpaint_enabled: bool = False
    beliefs_applied: list[str] = []
    # Phase 3 additive — multi-agent pipeline structured outputs.
    # Optional so the legacy single-classifier path keeps working when these are absent.
    icp: dict[str, Any] | None = None
    location_enrichment: dict[str, Any] | None = None
    reviews_evaluation: dict[str, Any] | None = None
    visual_system: dict[str, Any] | None = None
    photo_analysis: dict[str, Any] | None = None
    duration_seconds: int = 15
    # Editorial Judge metadata — set when Final Assembly's multi-sample path
    # ran 3 candidates and a Judge agent picked the strongest brief. None when
    # only one sample survived, the Judge call failed, or multi-sample was off.
    judge_score: float | None = None  # winner aggregate, 0–10
    judge_rationale: str | None = None  # 1–3 sentences, why the winner won
    judge_scores_per_brief: list[dict[str, Any]] | None = None  # per-brief detail


class Belief(BaseModel):
    rule_key: str  # e.g. "hook_with_hero_shot"
    rule_text: str  # human-readable rule the agent applies
    confidence: float  # 0.0–1.0


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


class RegenerateRequest(BaseModel):
    listing_url: str
    listing: ScrapedListing
    decision: AgentDecision


class RegenerateResponse(BaseModel):
    video_id: str
    decision: AgentDecision
