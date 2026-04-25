"""Pydantic models for the agent layer. All data shapes live here."""

from pydantic import BaseModel


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
