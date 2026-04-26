"""Pydantic models for the agent layer. All data shapes live here."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Language = Literal["de", "en", "es"]
Tone = Literal["luxury", "family", "urban", "cozy"]
HookKind = Literal["amenity", "location", "review", "view"]
EmphasisSource = Literal["amenity", "review", "location"]


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
    # Nearby venue photos (Google Places → Hera ``/files``). Passed as
    # ``reference_image_urls`` on create_video; not outpainted.
    neighborhood_reference_urls: list[str] = Field(default_factory=list)
    neighborhood_places: list[dict[str, Any]] = Field(default_factory=list)
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


class HookOption(BaseModel):
    id: str
    label: str
    kind: HookKind
    rationale: str


class EmphasisOption(BaseModel):
    slug: str
    label: str
    score: float
    source: EmphasisSource


class Phase1Decision(BaseModel):
    """Cheap-to-compute output of Phase 1. Returned to the user for approval
    before the expensive Phase 2 (photo analysis, final assembly, Hera render)
    is triggered. Round-trips through the frontend untouched."""

    icp: dict[str, Any] | None = None
    location_enrichment: dict[str, Any] | None = None
    reviews_evaluation: dict[str, Any] | None = None
    visual_system: dict[str, Any] | None = None
    suggested_language: Language = "en"
    suggested_tone: Tone = "cozy"
    emphasis_options: list[EmphasisOption] = Field(default_factory=list)
    hook_options: list[HookOption] = Field(default_factory=list)
    duration_seconds: int = 15
    outpaint_enabled: bool = False


class Overrides(BaseModel):
    """User edits applied on top of the Phase 1 suggestions. Sent back to the
    server with /api/generate to steer Phase 2."""

    language: Language
    tone: Tone
    emphasis: list[str] = Field(default_factory=list)
    deemphasis: list[str] = Field(default_factory=list)
    hook_id: str = "auto"


class ListingResponse(BaseModel):
    listing: ScrapedListing
    phase1: Phase1Decision


class GenerateRequest(BaseModel):
    listing_url: str
    listing: ScrapedListing
    phase1: Phase1Decision
    overrides: Overrides


class GenerateResponse(BaseModel):
    video_id: str
    decision: AgentDecision
    # videos.id from the Supabase insert. Required by /api/videos/{id}/publish
    # so the AgentApp's done screen can wire a one-click YouTube upload without
    # making the user travel to /dashboard. None when Supabase is unconfigured.
    internal_video_id: str | None = None


class RegenerateRequest(BaseModel):
    listing_url: str
    listing: ScrapedListing
    decision: AgentDecision


class RegenerateResponse(BaseModel):
    video_id: str
    decision: AgentDecision
