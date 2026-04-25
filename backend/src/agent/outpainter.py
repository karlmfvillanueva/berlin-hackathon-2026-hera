"""Outpaint top-5 photos to 9:16 portrait via Google's native nano-banana model.

Pipeline per photo:
  1. Download the source URL (the landscape Airbnb photo)
  2. Call Gemini's image-edit model (gemini-3.1-flash-image-preview) with the
     source bytes + a portrait-extension prompt → output JPEG bytes
  3. Upload the result to Supabase Storage bucket `outpainted-photos`
  4. Return the public URL Hera can fetch as a reference_image_url

5 photos run concurrently via asyncio.gather. Per-photo budget 30s. Any failure
(quota, network, bad bytes, missing Supabase, missing Gemini key) silently
falls back to the original URL — the output list always matches the input length
so downstream code never sees a missing image.

We use the native Gemini API instead of fal.ai's wrapper so the project only
needs one key (GEMINI_API_KEY) and a single SDK (google-genai).
"""

import asyncio
import uuid

import httpx
from google import genai
from google.genai import types

from src.logger import log
from src.supabase_client import get_supabase_client

_MODEL = "gemini-3.1-flash-image-preview"
_BUCKET = "outpainted-photos"
_PER_PHOTO_TIMEOUT = 30.0
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

            response = await gemini.aio.models.generate_content(
                model=_MODEL,
                contents=[
                    _OUTPAINT_PROMPT,
                    types.Part.from_bytes(data=src_bytes, mime_type="image/jpeg"),
                ],
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )

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

    import os

    api_key = os.getenv("GEMINI_API_KEY", "")
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase = get_supabase_client()

    if not api_key:
        log.warning("outpaint: GEMINI_API_KEY missing — returning originals")
        return list(urls)
    if supabase is None or not supabase_url:
        log.warning("outpaint: Supabase not configured — returning originals")
        return list(urls)

    gemini = genai.Client(api_key=api_key)
    log.info("outpaint: starting %d concurrent calls via %s", len(urls), _MODEL)
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(
            *(
                _outpaint_one(http, gemini, supabase, supabase_url, u)
                for u in urls
            )
        )
    return list(results)
