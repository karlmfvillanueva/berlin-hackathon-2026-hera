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

from src.logger import log

load_dotenv(dotenv_path="../.env")
load_dotenv()

HERA_API_KEY = os.getenv("HERA_API_KEY", "")
HERA_BASE_URL = "https://api.hera.video/v1"

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not HERA_API_KEY:
        log.warning("HERA_API_KEY is not set — /api/videos calls will fail")
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
