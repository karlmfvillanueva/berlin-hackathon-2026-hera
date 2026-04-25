"""FastAPI app proxying the Hera video API.

Hera reference: https://docs.hera.video/api-reference/introduction
The frontend never sees HERA_API_KEY — it stays on the server.
"""

import os
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent import (
    GenerateRequest,
    GenerateResponse,
    ListingResponse,
    RegenerateRequest,
    RegenerateResponse,
    load_fixture,
    run,
)
from src.agent.scraper import scrape_listing
from src.logger import log
from src.supabase_client import get_supabase_client

load_dotenv(dotenv_path="../credentials/credentials.env")
load_dotenv(dotenv_path="../.env")
load_dotenv()

HERA_API_KEY = os.getenv("HERA_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HERA_BASE_URL = "https://api.hera.video/v1"
ENABLE_LIVE_SCRAPE = os.getenv("ENABLE_LIVE_SCRAPE", "false").lower() == "true"

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not HERA_API_KEY:
        log.warning("HERA_API_KEY is not set — /api/videos calls will fail")
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY is not set — classifier will fail")
    app.state.http = httpx.AsyncClient(
        base_url=HERA_BASE_URL,
        headers={"x-api-key": HERA_API_KEY, "content-type": "application/json"},
        timeout=30.0,
    )
    log.info("Backend ready. Hera base=%s", HERA_BASE_URL)
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(title="Hera proxy", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Pydantic models matching the Hera OpenAPI spec ---

OutputFormat = Literal["mp4", "prores", "webm", "gif"]
AspectRatio = Literal["16:9", "9:16", "1:1", "4:5"]
Fps = Literal["24", "25", "30", "60"]
Resolution = Literal["360p", "480p", "720p", "1080p", "4k"]
JobStatus = Literal["in-progress", "success", "failed"]


class VideoOutputConfig(BaseModel):
    format: OutputFormat
    aspect_ratio: AspectRatio
    fps: Fps
    resolution: Resolution


class CreateVideoBody(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    duration_seconds: int | None = Field(default=None, ge=1, le=60)
    outputs: list[VideoOutputConfig] = Field(
        default_factory=lambda: [
            VideoOutputConfig(format="mp4", aspect_ratio="16:9", fps="30", resolution="1080p")
        ]
    )


class CreateVideoResponse(BaseModel):
    video_id: str
    project_url: str | None = None


class VideoOutputResult(BaseModel):
    status: JobStatus
    file_url: str | None = None
    config: VideoOutputConfig
    error: str | None = None


class GetVideoResponse(BaseModel):
    video_id: str
    project_url: str | None = None
    status: JobStatus
    outputs: list[VideoOutputResult] = []


# --- Routes ---


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, "hera_key_loaded": bool(HERA_API_KEY)}


@app.post("/api/videos", response_model=CreateVideoResponse)
async def create_video(body: CreateVideoBody) -> CreateVideoResponse:
    log.info("Creating Hera video job, prompt_chars=%d", len(body.prompt))
    payload = body.model_dump(exclude_none=True)
    try:
        r = await app.state.http.post("/videos", json=payload)
    except httpx.HTTPError as exc:
        log.exception("Hera request failed")
        raise HTTPException(status_code=502, detail=f"Hera unreachable: {exc}") from exc

    if r.status_code >= 400:
        log.error("Hera POST /videos %d: %s", r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.json() if r.content else None)
    return CreateVideoResponse(**r.json())


class ListingRequest(BaseModel):
    listing_url: str
    outpaint_enabled: bool = False


@app.post("/api/listing", response_model=ListingResponse)
async def get_listing(body: ListingRequest) -> ListingResponse:
    """Load a listing (fixture by default; live scrape behind ENABLE_LIVE_SCRAPE)."""
    log.info(
        "listing: url=%s outpaint_enabled=%s live_scrape=%s",
        body.listing_url,
        body.outpaint_enabled,
        ENABLE_LIVE_SCRAPE,
    )
    listing = load_fixture(body.listing_url)

    if listing is None and ENABLE_LIVE_SCRAPE:
        log.info("listing: fixture miss → live scrape url=%s", body.listing_url)
        listing = await scrape_listing(body.listing_url)
        if listing is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "scrape_blocked",
                    "message": "Could not read that listing. Try a different URL.",
                },
            )

    if listing is None:
        log.warning("listing: fixture not found for url=%s", body.listing_url)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "fixture_not_found",
                "message": f"No fixture for URL: {body.listing_url}",
            },  # noqa: E501
        )
    try:
        decision = await run(listing, outpaint_enabled=body.outpaint_enabled)
    except Exception as exc:
        log.exception("listing: classifier failed")
        raise HTTPException(
            status_code=500,
            detail={"error": "classifier_failed", "message": str(exc)},
        ) from exc
    return ListingResponse(listing=listing, decision=decision)


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_video(body: GenerateRequest) -> GenerateResponse:
    """Submit a Hera video job using a pre-computed AgentDecision."""
    payload = {
        "prompt": body.decision.hera_prompt,
        "duration_seconds": 15,
        "outputs": [{"format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p"}],
        "reference_image_urls": body.decision.selected_image_urls[:5],
    }
    log.info(
        "generate: submitting to Hera. prompt_chars=%d images=%d",
        len(body.decision.hera_prompt),
        len(payload["reference_image_urls"]),
    )
    try:
        r = await app.state.http.post("/videos", json=payload)
    except httpx.HTTPError as exc:
        log.exception("generate: Hera unreachable")
        raise HTTPException(
            status_code=502,
            detail={"error": "hera_unreachable", "message": str(exc)},
        ) from exc

    if r.status_code >= 400:
        log.error("generate: Hera POST /videos %d: %s", r.status_code, r.text[:500])
        raise HTTPException(
            status_code=500,
            detail={"error": "hera_submission_failed", "message": r.text[:300]},
        )

    hera_response = r.json()
    video_id = hera_response["video_id"]
    log.info("generate: Hera accepted job video_id=%s", video_id)

    # B-05: best-effort persistence. Never block the user on a Supabase outage.
    supabase = get_supabase_client()
    if supabase is not None:
        try:
            supabase.table("videos").insert(
                {
                    "listing_url": body.listing_url,
                    "hera_video_id": video_id,
                    "hera_project_url": hera_response.get("project_url"),
                    "video_url": None,
                    "outpaint_enabled": body.decision.outpaint_enabled,
                    "listing_data": body.listing.model_dump(),
                    "agent_decision": body.decision.model_dump(),
                    "hera_payload": payload,
                }
            ).execute()
            log.info("supabase: persisted video_id=%s", video_id)
        except Exception as exc:
            log.error("supabase: insert failed video_id=%s err=%s", video_id, exc)

    return GenerateResponse(video_id=video_id, decision=body.decision)


@app.post("/api/regenerate", response_model=RegenerateResponse)
async def regenerate_video(body: RegenerateRequest) -> RegenerateResponse:
    """Re-submit an existing AgentDecision to Hera for a fresh render.

    No re-classification — same decision in, new video_id out.
    """
    payload = {
        "prompt": body.decision.hera_prompt,
        "duration_seconds": 15,
        "outputs": [{"format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p"}],
        "reference_image_urls": body.decision.selected_image_urls[:5],
    }
    log.info(
        "regenerate: resubmitting to Hera. listing_url=%s prompt_chars=%d images=%d",
        body.listing_url,
        len(body.decision.hera_prompt),
        len(payload["reference_image_urls"]),
    )
    try:
        r = await app.state.http.post("/videos", json=payload)
    except httpx.HTTPError as exc:
        log.exception("regenerate: Hera unreachable")
        raise HTTPException(
            status_code=502,
            detail={"error": "hera_unreachable", "message": str(exc)},
        ) from exc

    if r.status_code >= 400:
        log.error("regenerate: Hera POST /videos %d: %s", r.status_code, r.text[:500])
        raise HTTPException(
            status_code=500,
            detail={"error": "hera_submission_failed", "message": r.text[:300]},
        )

    video_id = r.json()["video_id"]
    log.info("regenerate: Hera accepted job video_id=%s", video_id)
    return RegenerateResponse(video_id=video_id, decision=body.decision)


@app.get("/api/videos/{video_id}", response_model=GetVideoResponse)
async def get_video(video_id: str) -> GetVideoResponse:
    try:
        r = await app.state.http.get(f"/videos/{video_id}")
    except httpx.HTTPError as exc:
        log.exception("Hera request failed")
        raise HTTPException(status_code=502, detail=f"Hera unreachable: {exc}") from exc

    if r.status_code >= 400:
        log.error("Hera GET /videos/%s %d: %s", video_id, r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.json() if r.content else None)
    return GetVideoResponse(**r.json())
