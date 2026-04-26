"""FastAPI app proxying the Hera video API.

Hera reference: https://docs.hera.video/api-reference/introduction
The frontend never sees HERA_API_KEY — it stays on the server.
"""

import os
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src import belief_evolution as belief_evo
from src import youtube as yt_lib
from src.agent import (
    GenerateRequest,
    GenerateResponse,
    ListingResponse,
    RegenerateRequest,
    RegenerateResponse,
    load_fixture,
    run_render_from_plan,
    run_storyboard_plan,
)
from src.agent.fixture_loader import fixture_room_ids
from src.agent.scraper import scrape_listing
from src.auth import AuthenticatedUser, current_user
from src.limits import LIMIT_GENERATE, LIMIT_LISTING, LIMIT_METRICS_REFRESH, LIMIT_PUBLISH, limiter
from src.logger import log
from src.supabase_client import get_supabase_client

load_dotenv(dotenv_path="../credentials/credentials.env")
load_dotenv(dotenv_path="../.env")
load_dotenv()

HERA_API_KEY = os.getenv("HERA_API_KEY", "")
GCP_PROJECT = os.getenv("GCP_PROJECT", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
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
    if not GCP_PROJECT:
        log.warning("GCP_PROJECT is not set — Gemini classifier + outpainter will fail")
    else:
        log.info("Vertex AI: project=%s location=%s", GCP_PROJECT, GCP_LOCATION)
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

# slowapi: limiter on app.state, exception handler, middleware that injects request
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _ratelimit_handler(_request: Request, exc: RateLimitExceeded) -> HTTPException:
    raise HTTPException(
        status_code=429,
        detail={"error": "rate_limited", "message": str(exc.detail)},
    )


app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*", "authorization"],
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


class DemoListing(BaseModel):
    """Pre-scraped listing the demo-mode UI surfaces as a picker card."""

    room_id: str
    listing_url: str
    title: str
    location: str
    cover_photo_url: str | None = None
    rating_overall: float | None = None
    reviews_count: int | None = None


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    require_auth: bool
    is_team_member: bool
    demo_listings: list[DemoListing]


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]


def _is_team_member(email: str | None) -> bool:
    """Lookup against the team_members allowlist. Service-role only — RLS would
    block authenticated reads. Falsy on every error so a Supabase outage can't
    accidentally promote a user to team status."""
    if not email:
        return False
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        res = (
            supabase.table("team_members")
            .select("email")
            .eq("email", email.lower())
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception as exc:  # noqa: BLE001
        log.error("team_members: lookup failed email=%s err=%s", email, exc)
        return False


def _build_demo_listings() -> list[DemoListing]:
    """Materialise the picker cards for demo mode from the fixture set."""
    items: list[DemoListing] = []
    for room_id in fixture_room_ids():
        # Build a real-shaped Airbnb URL so the existing /api/listing flow
        # accepts it unchanged — the fixture loader matches by room ID.
        synthetic_url = f"https://www.airbnb.com/rooms/{room_id}"
        listing = load_fixture(synthetic_url)
        if listing is None:
            continue
        items.append(
            DemoListing(
                room_id=room_id,
                listing_url=synthetic_url,
                title=listing.title,
                location=listing.location,
                cover_photo_url=listing.photos[0].url if listing.photos else None,
                rating_overall=listing.rating_overall,
                reviews_count=listing.reviews_count,
            )
        )
    return items


@app.get("/api/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    """Returns the JWT-resolved user plus the team-membership flag and the
    curated demo-listing set. The frontend uses these to decide whether to
    show the free-text URL input (team only) or only the demo picker cards."""
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        require_auth=os.getenv("REQUIRE_AUTH", "true").lower() != "false",
        is_team_member=_is_team_member(user.email),
        demo_listings=_build_demo_listings(),
    )


@app.post("/api/videos", response_model=CreateVideoResponse)
async def create_video(
    body: CreateVideoBody,
    _user: CurrentUser,
) -> CreateVideoResponse:
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
@limiter.limit(LIMIT_LISTING)
async def get_listing(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: ListingRequest,
    user: CurrentUser,
) -> ListingResponse:
    """Load a listing. Demo-mode users (non-team) are restricted to the
    pre-scraped fixture set so the demo can't be broken by a missing/blocked
    Airbnb URL. Team members fall through to live scrape (Playwright →
    ScraperAPI) as before."""
    is_team = _is_team_member(user.email)
    log.info(
        "listing: url=%s outpaint_enabled=%s live_scrape=%s is_team=%s",
        body.listing_url,
        body.outpaint_enabled,
        ENABLE_LIVE_SCRAPE,
        is_team,
    )
    listing = load_fixture(body.listing_url)

    if listing is None and not is_team:
        # Demo-mode rail: refuse anything outside the fixture set so the front-
        # end's picker contract stays honest. Frontend should never hit this in
        # normal flow; if it does, the user crafted a URL by hand.
        log.warning(
            "listing: non-team user attempted non-fixture URL email=%s url=%s",
            user.email,
            body.listing_url,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "demo_mode_only",
                "message": "Pick one of the demo listings to try the agent.",
            },
        )

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
        phase1 = run_storyboard_plan(listing, outpaint_enabled=body.outpaint_enabled)
    except Exception as exc:
        log.exception("listing: phase1 pipeline failed")
        raise HTTPException(
            status_code=500,
            detail={"error": "classifier_failed", "message": str(exc)},
        ) from exc
    return ListingResponse(listing=listing, phase1=phase1)


@app.post("/api/generate", response_model=GenerateResponse)
@limiter.limit(LIMIT_GENERATE)
async def generate_video(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: GenerateRequest,
    user: CurrentUser,
) -> GenerateResponse:
    """Phase 2: run the heavy agents with user overrides, then submit to Hera."""
    try:
        decision = await run_render_from_plan(body.listing, body.phase1, body.overrides)
    except Exception as exc:
        log.exception("generate: phase2 pipeline failed")
        raise HTTPException(
            status_code=500,
            detail={"error": "render_pipeline_failed", "message": str(exc)},
        ) from exc

    # Hera's reference_image_urls is for brand/style references (logo, palette).
    # Listing content photos go in assets[] with type=image.
    image_assets = [{"type": "image", "url": u} for u in decision.selected_image_urls[:5]]
    payload = {
        "prompt": decision.hera_prompt,
        "duration_seconds": decision.duration_seconds,
        "outputs": [{"format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p"}],
        "assets": image_assets,
    }
    log.info(
        "generate: submitting to Hera. prompt_chars=%d images=%d lang=%s tone=%s",
        len(decision.hera_prompt),
        len(image_assets),
        body.overrides.language,
        body.overrides.tone,
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
    internal_video_id: str | None = None
    supabase = get_supabase_client()
    if supabase is not None:
        try:
            insert_res = (
                supabase.table("videos")
                .insert(
                    {
                        "user_id": user.user_id,
                        "listing_url": body.listing_url,
                        "hera_video_id": video_id,
                        "hera_project_url": hera_response.get("project_url"),
                        "video_url": None,
                        "outpaint_enabled": decision.outpaint_enabled,
                        "listing_data": body.listing.model_dump(),
                        "agent_decision": decision.model_dump(),
                        "hera_payload": payload,
                    }
                )
                .execute()
            )
            rows = insert_res.data or []
            if rows:
                internal_video_id = rows[0].get("id")
            log.info(
                "supabase: persisted video_id=%s internal_id=%s",
                video_id,
                internal_video_id,
            )
        except Exception as exc:
            log.error("supabase: insert failed video_id=%s err=%s", video_id, exc)

    return GenerateResponse(
        video_id=video_id, decision=decision, internal_video_id=internal_video_id
    )


@app.post("/api/regenerate", response_model=RegenerateResponse)
@limiter.limit(LIMIT_GENERATE)
async def regenerate_video(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: RegenerateRequest,
    _user: CurrentUser,
) -> RegenerateResponse:
    """Re-submit an existing AgentDecision to Hera for a fresh render.

    No re-classification — same decision in, new video_id out.
    """
    image_assets = [{"type": "image", "url": u} for u in body.decision.selected_image_urls[:5]]
    payload = {
        "prompt": body.decision.hera_prompt,
        "duration_seconds": body.decision.duration_seconds,
        "outputs": [{"format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p"}],
        "assets": image_assets,
    }
    log.info(
        "regenerate: resubmitting to Hera. listing_url=%s prompt_chars=%d images=%d",
        body.listing_url,
        len(body.decision.hera_prompt),
        len(image_assets),
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
async def get_video(
    video_id: str,
    _user: CurrentUser,
) -> GetVideoResponse:
    try:
        r = await app.state.http.get(f"/videos/{video_id}")
    except httpx.HTTPError as exc:
        log.exception("Hera request failed")
        raise HTTPException(status_code=502, detail=f"Hera unreachable: {exc}") from exc

    if r.status_code >= 400:
        log.error("Hera GET /videos/%s %d: %s", video_id, r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.json() if r.content else None)
    return GetVideoResponse(**r.json())


# --- YouTube OAuth + status ---


class YouTubeConnectURL(BaseModel):
    url: str


@app.get("/api/youtube/connect-url", response_model=YouTubeConnectURL)
async def youtube_connect_url(user: CurrentUser) -> YouTubeConnectURL:
    """Returns the Google consent URL the frontend should send the user to.
    State is signed with the JWT secret + carries the user_id, so the callback
    binds the exchange to the right user without server-side session storage."""
    try:
        url = yt_lib.build_consent_url(user.user_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "youtube_oauth_not_configured", "message": str(exc)},
        ) from exc
    return YouTubeConnectURL(url=url)


@app.get("/api/youtube/callback")
async def youtube_callback(code: str | None = None, state: str | None = None) -> RedirectResponse:
    """OAuth-redirect target. Verifies state, exchanges code, persists tokens.
    Redirects back to the SPA dashboard with a success or error flag in the
    query string."""
    base = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    dashboard_url = f"{base}/dashboard"

    if not code or not state:
        return RedirectResponse(url=f"{dashboard_url}?youtube_error=missing_params")

    try:
        user_id = yt_lib.verify_state(state)
    except ValueError:
        return RedirectResponse(url=f"{dashboard_url}?youtube_error=bad_state")

    try:
        result = yt_lib.complete_oauth(user_id, code)
    except Exception as exc:  # noqa: BLE001 — OAuth surface is wide
        log.exception("youtube: callback failed user=%s", user_id)
        return RedirectResponse(
            url=f"{dashboard_url}?youtube_error=exchange_failed&detail={type(exc).__name__}"
        )

    if not result["connected"] and result.get("error") == "no_channel":
        return RedirectResponse(url=f"{dashboard_url}?youtube_error=no_channel")
    return RedirectResponse(url=f"{dashboard_url}?youtube_connected=1")


class YouTubeStatus(BaseModel):
    connected: bool
    channel_id: str | None = None
    channel_title: str | None = None
    expires_soon: bool = False


@app.get("/api/youtube/status", response_model=YouTubeStatus)
async def youtube_status(user: CurrentUser) -> YouTubeStatus:
    return YouTubeStatus(**yt_lib.get_status(user.user_id))


@app.post("/api/youtube/disconnect")
async def youtube_disconnect(user: CurrentUser) -> dict[str, bool]:
    yt_lib.disconnect(user.user_id)
    return {"ok": True}


# --- Publish to YouTube + metrics + dashboard ---


class PublishRequest(BaseModel):
    visibility: Literal["unlisted", "public", "private"] = "unlisted"
    title: str | None = None
    description: str | None = None


class PublishResponse(BaseModel):
    youtube_video_id: str
    youtube_channel_id: str | None
    visibility: str
    published_at: str | None


def _looked_up_video_row(supabase: Any, internal_video_id: str, user_id: str) -> dict[str, Any]:
    res = (
        supabase.table("videos")
        .select("*")
        .eq("id", internal_video_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail={"error": "video_not_found"})
    return rows[0]


@app.post("/api/videos/{internal_video_id}/publish", response_model=PublishResponse)
@limiter.limit(LIMIT_PUBLISH)
async def publish_to_youtube(
    request: Request,  # noqa: ARG001 — required by slowapi
    internal_video_id: str,
    body: PublishRequest,
    user: CurrentUser,
) -> PublishResponse:
    """Pull the rendered MP4 from Hera and upload it to the user's YouTube channel.

    The internal_video_id is our DB row's UUID (videos.id), not Hera's video_id.
    We resolve to the Hera id, fetch the file_url, stream the bytes into the
    YouTube resumable-upload helper, and persist the YouTube id/channel back."""
    supabase = get_supabase_client()
    if supabase is None:
        raise HTTPException(status_code=503, detail={"error": "supabase_unavailable"})

    row = _looked_up_video_row(supabase, internal_video_id, user.user_id)
    hera_video_id = row.get("hera_video_id")
    if not hera_video_id:
        raise HTTPException(status_code=409, detail={"error": "no_hera_video_id"})

    # 1. Get the rendered file_url from Hera.
    try:
        r = await app.state.http.get(f"/videos/{hera_video_id}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail={"error": "hera_unreachable"}) from exc
    if r.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={"error": "hera_lookup_failed", "message": r.text[:300]},
        )
    hera_payload = r.json()
    if hera_payload.get("status") != "success":
        raise HTTPException(status_code=409, detail={"error": "video_not_ready"})
    outputs = hera_payload.get("outputs") or []
    file_url = outputs[0].get("file_url") if outputs else None
    if not file_url:
        raise HTTPException(status_code=409, detail={"error": "no_file_url"})

    # 2. Download the MP4 (stream into memory; Shorts are small).
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(file_url)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail={"error": "hera_file_download_failed", "status": resp.status_code},
            )
        video_bytes = resp.content

    # 3. Upload to YouTube via resumable upload.
    listing_data = row.get("listing_data") or {}
    decision = row.get("agent_decision") or {}
    persona = ((decision.get("icp") or {}).get("best_icp") or {}).get("persona")
    title = body.title or _build_title(listing_data, persona)
    description = body.description or _build_description(listing_data, decision)

    try:
        result = yt_lib.upload_video(
            user_id=user.user_id,
            video_bytes=video_bytes,
            title=title,
            description=description,
            visibility=body.visibility,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "youtube_not_connected", "message": str(exc)},
        ) from exc
    except Exception as exc:  # noqa: BLE001 — googleapiclient surfaces many error types
        log.exception("publish: YouTube upload failed video=%s", internal_video_id)
        raise HTTPException(
            status_code=502,
            detail={"error": "youtube_upload_failed", "message": str(exc)[:300]},
        ) from exc

    # 4. Persist YouTube metadata back to videos row.
    update_payload = {
        "youtube_video_id": result.get("video_id"),
        "youtube_channel_id": result.get("channel_id"),
        "published_at": result.get("published_at"),
        "visibility": body.visibility,
    }
    try:
        supabase.table("videos").update(update_payload).eq("id", internal_video_id).execute()
    except Exception as exc:  # noqa: BLE001
        log.error("publish: persist failed video=%s err=%s", internal_video_id, exc)

    return PublishResponse(
        youtube_video_id=result.get("video_id") or "",
        youtube_channel_id=result.get("channel_id"),
        visibility=body.visibility,
        published_at=result.get("published_at"),
    )


def _build_title(listing_data: dict[str, Any], persona: str | None) -> str:
    title = listing_data.get("title") or "Stay"
    suffix = f" · for {persona}" if persona else ""
    full = f"{title}{suffix}"
    return full[:95]


def _build_description(listing_data: dict[str, Any], decision: dict[str, Any]) -> str:
    parts = []
    url = listing_data.get("url")
    if url:
        parts.append(f"Book this stay: {url}")
    angle = decision.get("angle")
    if isinstance(angle, str) and angle and angle != "—":
        parts.append("")
        parts.append(angle)
    parts.append("")
    parts.append(
        "Generated by Hera × the editorial agent — opinions about hook, angle, and pacing."
    )
    return "\n".join(parts)[:4900]


# --- Metrics + dashboard ---


class MetricsRefreshResponse(BaseModel):
    view_count: int
    like_count: int
    comment_count: int
    observed_at: str


@app.post(
    "/api/videos/{internal_video_id}/metrics/refresh",
    response_model=MetricsRefreshResponse,
)
@limiter.limit(LIMIT_METRICS_REFRESH)
async def refresh_metrics(
    request: Request,  # noqa: ARG001 — required by slowapi
    internal_video_id: str,
    user: CurrentUser,
) -> MetricsRefreshResponse:
    supabase = get_supabase_client()
    if supabase is None:
        raise HTTPException(status_code=503, detail={"error": "supabase_unavailable"})

    row = _looked_up_video_row(supabase, internal_video_id, user.user_id)
    yt_id = row.get("youtube_video_id")
    if not yt_id:
        raise HTTPException(status_code=409, detail={"error": "not_published"})

    try:
        stats = yt_lib.fetch_statistics(user.user_id, yt_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "youtube_not_connected", "message": str(exc)},
        ) from exc

    snapshot = {
        "video_id": internal_video_id,
        "view_count": stats.get("view_count", 0),
        "like_count": stats.get("like_count", 0),
        "comment_count": stats.get("comment_count", 0),
        "is_demo_seed": False,
    }
    res = supabase.table("video_metrics_snapshot").insert(snapshot).execute()
    rows = res.data or []
    observed_at = rows[0].get("observed_at") if rows else ""
    return MetricsRefreshResponse(
        view_count=snapshot["view_count"],
        like_count=snapshot["like_count"],
        comment_count=snapshot["comment_count"],
        observed_at=observed_at or "",
    )


class DashboardVideo(BaseModel):
    id: str
    listing_url: str
    listing_title: str | None = None
    persona: str | None = None
    youtube_video_id: str | None = None
    published_at: str | None = None
    is_demo_seed: bool = False
    latest_view_count: int | None = None
    latest_like_count: int | None = None


class DashboardAggregate(BaseModel):
    total_videos: int
    total_published: int
    total_views: int
    top_performer_id: str | None = None


class DashboardResponse(BaseModel):
    videos: list[DashboardVideo]
    aggregate: DashboardAggregate


@app.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user: CurrentUser,
    include_demo: bool = True,
) -> DashboardResponse:
    """Returns the user's videos plus optional demo-seeded mock videos.

    Each video carries the latest snapshot stats inline so the dashboard list
    can render sparkline previews + headline metrics without N+1 calls."""
    supabase = get_supabase_client()
    if supabase is None:
        return DashboardResponse(
            videos=[],
            aggregate=DashboardAggregate(total_videos=0, total_published=0, total_views=0),
        )

    user_videos_res = (
        supabase.table("videos").select("*").eq("user_id", user.user_id).execute()
    )
    user_rows = user_videos_res.data or []

    demo_rows: list[dict[str, Any]] = []
    if include_demo:
        # Demo seed videos have user_id = NULL; selected separately.
        demo_res = supabase.table("videos").select("*").is_("user_id", "null").execute()
        demo_rows = demo_res.data or []

    all_rows = user_rows + demo_rows
    if not all_rows:
        return DashboardResponse(
            videos=[],
            aggregate=DashboardAggregate(total_videos=0, total_published=0, total_views=0),
        )

    # Pull latest snapshot per video in one batch.
    ids = [r["id"] for r in all_rows]
    snap_res = (
        supabase.table("video_metrics_snapshot")
        .select("video_id, view_count, like_count, observed_at")
        .in_("video_id", ids)
        .order("observed_at", desc=True)
        .execute()
    )
    snap_rows = snap_res.data or []
    latest_by_video: dict[str, dict[str, Any]] = {}
    for s in snap_rows:
        vid = s["video_id"]
        if vid not in latest_by_video:
            latest_by_video[vid] = s

    videos: list[DashboardVideo] = []
    total_views = 0
    top_id: str | None = None
    top_views = -1
    for row in all_rows:
        decision = row.get("agent_decision") or {}
        listing_data = row.get("listing_data") or {}
        persona = ((decision.get("icp") or {}).get("best_icp") or {}).get("persona")
        snap = latest_by_video.get(row["id"]) or {}
        view_count = snap.get("view_count")
        if isinstance(view_count, int):
            total_views += view_count
            if view_count > top_views:
                top_views = view_count
                top_id = row["id"]
        videos.append(
            DashboardVideo(
                id=row["id"],
                listing_url=row.get("listing_url") or "",
                listing_title=listing_data.get("title"),
                persona=persona,
                youtube_video_id=row.get("youtube_video_id"),
                published_at=row.get("published_at"),
                is_demo_seed=row.get("user_id") is None,
                latest_view_count=view_count if isinstance(view_count, int) else None,
                latest_like_count=snap.get("like_count")
                if isinstance(snap.get("like_count"), int)
                else None,
            )
        )

    aggregate = DashboardAggregate(
        total_videos=len(videos),
        total_published=sum(1 for v in videos if v.youtube_video_id),
        total_views=total_views,
        top_performer_id=top_id,
    )
    return DashboardResponse(videos=videos, aggregate=aggregate)


class TimeseriesPoint(BaseModel):
    observed_at: str
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    avg_view_duration_s: float | None = None
    retention_50pct: float | None = None


@app.get(
    "/api/videos/{internal_video_id}/timeseries",
    response_model=list[TimeseriesPoint],
)
async def get_timeseries(internal_video_id: str, user: CurrentUser) -> list[TimeseriesPoint]:
    """Returns ALL snapshots for a video, oldest → newest. Demo-seed videos
    bypass ownership check via the migration's RLS policy; user-owned ones
    require user_id match."""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    # Verify ownership OR demo: a single SELECT with the right filter.
    video_res = supabase.table("videos").select("user_id").eq("id", internal_video_id).execute()
    if not video_res.data:
        raise HTTPException(status_code=404, detail={"error": "video_not_found"})
    video_owner = video_res.data[0].get("user_id")
    if video_owner is not None and video_owner != user.user_id:
        raise HTTPException(status_code=403, detail={"error": "not_owner"})

    snap_res = (
        supabase.table("video_metrics_snapshot")
        .select("observed_at, view_count, like_count, comment_count, "
                "avg_view_duration_s, retention_50pct")
        .eq("video_id", internal_video_id)
        .order("observed_at", desc=False)
        .execute()
    )
    rows = snap_res.data or []
    return [TimeseriesPoint(**r) for r in rows]


# --- Belief evolution (demo) ---


class BeliefEvolutionItem(BaseModel):
    rule_key: str
    rule_text: str
    current_confidence: float
    new_confidence: float
    sample_size: int
    retention_delta: float
    rationale: str
    is_demo: bool


class BeliefEvolutionResponse(BaseModel):
    items: list[BeliefEvolutionItem]
    is_demo_data: bool


@app.get("/api/beliefs/evolution", response_model=BeliefEvolutionResponse)
async def get_belief_evolution(_user: CurrentUser) -> BeliefEvolutionResponse:
    """Computes belief-confidence updates from collected metrics.

    Reads the seed beliefs + every video + their snapshots, then maps belief
    application to retention deltas vs. baseline. Demo-seed videos contribute
    when no real data exists yet — the response flags `is_demo_data=true` so
    the UI can show a 'demo' badge."""
    supabase = get_supabase_client()
    if supabase is None:
        return BeliefEvolutionResponse(items=[], is_demo_data=False)

    beliefs_res = supabase.table("agent_beliefs").select("*").execute()
    videos_res = supabase.table("videos").select("id, user_id, agent_decision").execute()
    snaps_res = (
        supabase.table("video_metrics_snapshot")
        .select("video_id, observed_at, retention_50pct, is_demo_seed")
        .execute()
    )

    items = belief_evo.simulate_evolution(
        beliefs=beliefs_res.data or [],
        videos=videos_res.data or [],
        snapshots=snaps_res.data or [],
    )
    is_demo_data = any(b.is_demo for b in items)
    return BeliefEvolutionResponse(
        items=[BeliefEvolutionItem(**vars(b)) for b in items],
        is_demo_data=is_demo_data,
    )


# --- Static frontend (Railway / single-container deploy) ---
# Dev mode (uvicorn --reload from /backend, frontend on :5173): the static
# directory does not exist, so this block is a no-op and CORS keeps cross-origin
# fetches working. Production: the Dockerfile copies frontend/dist → backend/static
# and the SPA is served same-origin, eliminating CORS entirely.

from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.exists():
    log.info("static: mounting %s as SPA root", _STATIC_DIR)

    class _SPAStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):  # type: ignore[override]
            # Starlette's StaticFiles RAISES HTTPException(404) on a missing
            # file — it does NOT return a 404 response — so the previous
            # `response.status_code == 404` check never fired and the SPA
            # client-side routes (/dashboard, /login, …) bubbled up as
            # FastAPI's `{"detail":"Not Found"}`. Catch the raise instead.
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code == 404:
                    return await super().get_response("index.html", scope)
                raise

    app.mount("/", _SPAStaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
else:
    log.info("static: %s not present — running in API-only / dev mode", _STATIC_DIR)
