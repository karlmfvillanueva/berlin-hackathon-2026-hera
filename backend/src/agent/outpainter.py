"""Outpaint top-5 photos to 9:16 portrait via Google's nano-banana image model.

Pipeline per photo:
  1. Download the source URL (the landscape Airbnb photo)
  2. Call Gemini's image-edit model on Vertex AI with the source bytes + a
     portrait-extension prompt → output JPEG bytes
  3. Upload the result to Supabase Storage bucket `outpainted-photos`
  4. Return the public URL Hera can fetch as a reference_image_url

5 photos run concurrently via asyncio.gather. Per-photo budget 30s. Any failure
(quota, network, bad bytes, missing Supabase, missing GCP config) silently
falls back to the original URL — the output list always matches the input length
so downstream code never sees a missing image.

Auth: Application Default Credentials (ADC) via Vertex AI. Same project /
location as the classifier. Model is env-overridable so a 3.x preview ID can
be dropped in once the GCP project gets allowlisted.
"""

import asyncio
import os
import uuid

import httpx
from google import genai
from google.genai import types

from src.logger import log
from src.supabase_client import get_supabase_client

_MODEL = os.getenv("GEMINI_OUTPAINT_MODEL", "gemini-2.5-flash-image")
_BUCKET = "outpainted-photos"
_PER_PHOTO_TIMEOUT = 30.0
# 5 parallel uploads can exhaust macOS SSL/socket pools (Errno 35 EAGAIN);
# 3 keeps total latency basically identical and gives clean 5/5 success.
_MAX_PARALLEL = 3
_OUTPAINT_PROMPT = (
    "Extend this image vertically to a 9:16 portrait aspect ratio. "
    "Add natural ceiling above and floor below, matching lighting, perspective, "
    "and decor. Keep the original subject centred and untouched."
)


def _public_url(supabase_url: str, path: str) -> str:
    """Build the public-read URL for a stored object."""
    return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{_BUCKET}/{path}"


async def _download(http: httpx.AsyncClient, url: str) -> bytes:
    r = await http.get(url, timeout=_PER_PHOTO_TIMEOUT)
    r.raise_for_status()
    return r.content


async def _outpaint_one(
    http: httpx.AsyncClient,
    gemini: genai.Client,
    supabase,
    supabase_url: str,
    src_url: str,
) -> str:
    """Outpaint one URL to 9:16 portrait. On any failure return the original URL."""
    try:
        async with asyncio.timeout(_PER_PHOTO_TIMEOUT):
            src_bytes = await _download(http, src_url)

            response = await _generate_with_retry(gemini, src_bytes)

            out_bytes, mime = _extract_image(response)
            if out_bytes is None:
                log.warning("outpaint: no image in response, fallback. src=%s", src_url[:60])
                return src_url

            ext = "jpg" if "jpeg" in mime else mime.split("/")[-1]
            path = f"{uuid.uuid4().hex}.{ext}"
            # supabase-py upload is sync; push it off the event loop
            await asyncio.to_thread(
                supabase.storage.from_(_BUCKET).upload,
                path,
                out_bytes,
                {"content-type": mime, "upsert": "false"},
            )
            new_url = _public_url(supabase_url, path)
            log.info(
                "outpaint: ok src=%s out=%s (%d bytes)",
                src_url[:60],
                new_url[-90:],
                len(out_bytes),
            )
            return new_url
    except (httpx.HTTPError, TimeoutError, ValueError, RuntimeError) as exc:
        log.warning("outpaint: fallback to original. src=%s reason=%s", src_url[:60], exc)
        return src_url
    except Exception as exc:  # noqa: BLE001 — protect the batch from any oddity
        log.warning(
            "outpaint: unexpected error, fallback. src=%s reason=%s: %s",
            src_url[:60],
            type(exc).__name__,
            str(exc)[:120],
        )
        return src_url


async def _generate_with_retry(gemini: genai.Client, src_bytes: bytes):
    """Single retry-on-429 with backoff. Vertex AI rate-limits image-edit calls
    aggressively when 3 land in the same second; one ~3s wait is usually enough."""
    for attempt in (0, 1):
        try:
            return await gemini.aio.models.generate_content(
                model=_MODEL,
                contents=[
                    _OUTPAINT_PROMPT,
                    types.Part.from_bytes(data=src_bytes, mime_type="image/jpeg"),
                ],
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
        except Exception as exc:  # noqa: BLE001 — bare so we can sniff for 429
            is_429 = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            if attempt == 0 and is_429:
                log.info("outpaint: 429 from Vertex, retrying after 3s")
                await asyncio.sleep(3.0)
                continue
            raise


def _extract_image(response) -> tuple[bytes | None, str]:
    """Pull the first inline_data image part out of a Gemini response."""
    try:
        parts = response.candidates[0].content.parts or []
    except (AttributeError, IndexError):
        return None, ""
    for p in parts:
        inline = getattr(p, "inline_data", None)
        if inline and inline.data:
            return inline.data, inline.mime_type or "image/jpeg"
    return None, ""


async def outpaint_5_photos(urls: list[str]) -> list[str]:
    """Outpaint all input URLs to 9:16 in parallel. Length is always preserved."""
    if not urls:
        return []

    project = os.getenv("GCP_PROJECT", "").strip()
    location = os.getenv("GCP_LOCATION", "us-central1").strip()
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase = get_supabase_client()

    if not project:
        log.warning("outpaint: GCP_PROJECT missing — returning originals")
        return list(urls)
    if supabase is None or not supabase_url:
        log.warning("outpaint: Supabase not configured — returning originals")
        return list(urls)

    gemini = genai.Client(vertexai=True, project=project, location=location)
    log.info(
        "outpaint: starting %d calls via %s (max_parallel=%d)",
        len(urls),
        _MODEL,
        _MAX_PARALLEL,
    )
    sem = asyncio.Semaphore(_MAX_PARALLEL)

    async def _gated(u: str) -> str:
        async with sem:
            return await _outpaint_one(http, gemini, supabase, supabase_url, u)

    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*(_gated(u) for u in urls))
    return list(results)
