"""Nanobanana (fal.ai) outpainter.

Takes the top-5 ranked landscape photo URLs and outpaints each to 9:16 portrait
so Hera receives properly-composed vertical reference images.

API surface (verified 2026-04, fal.ai):
  POST https://fal.run/fal-ai/nano-banana/edit
  Header: Authorization: Key $NANOBANANA_API_KEY
  Body:   {prompt, image_urls: [url], aspect_ratio: "9:16", output_format: "jpeg"}
  Reply:  {images: [{url, width, height, ...}], description}

Behaviour contract:
  * Output list always has the same length as the input — fallback to original URL
    on any per-photo failure (timeout, HTTP error, malformed response).
  * 5 calls run concurrently via asyncio.gather.
  * Per-photo budget: 30s wall-clock (matches architecture doc Layer 4).
  * If NANOBANANA_API_KEY is missing, returns originals untouched.
"""

import asyncio
import os

import httpx

from src.logger import log

_FAL_ENDPOINT = "https://fal.run/fal-ai/nano-banana/edit"
_PER_PHOTO_TIMEOUT = 30.0
_OUTPAINT_PROMPT = (
    "Extend this image vertically to a 9:16 portrait aspect ratio. "
    "Add natural ceiling above and floor below, matching lighting, perspective, "
    "and decor. Keep the original subject centred and untouched."
)


async def _outpaint_one(client: httpx.AsyncClient, url: str) -> str:
    """Outpaint one URL to 9:16. On any failure return the original URL."""
    payload = {
        "prompt": _OUTPAINT_PROMPT,
        "image_urls": [url],
        "aspect_ratio": "9:16",
        "output_format": "jpeg",
    }
    try:
        r = await client.post(_FAL_ENDPOINT, json=payload)
        if r.status_code >= 400:
            log.warning(
                "outpaint: fal returned %d, falling back to original. body=%s",
                r.status_code,
                r.text[:200],
            )
            return url
        data = r.json()
        new_url = data["images"][0]["url"]
        log.info("outpaint: ok original=%s outpainted=%s", url[:60], new_url[:60])
        return new_url
    except (httpx.HTTPError, TimeoutError, KeyError, IndexError) as exc:
        log.warning("outpaint: fallback to original. url=%s reason=%s", url[:60], exc)
        return url


async def outpaint_5_photos(urls: list[str]) -> list[str]:
    """Outpaint all input URLs to 9:16 in parallel. Length is preserved."""
    api_key = os.getenv("NANOBANANA_API_KEY", "")
    if not api_key:
        log.warning("outpaint: NANOBANANA_API_KEY missing — returning originals")
        return list(urls)

    if not urls:
        return []

    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }
    log.info("outpaint: starting %d concurrent calls", len(urls))
    async with httpx.AsyncClient(headers=headers, timeout=_PER_PHOTO_TIMEOUT) as client:
        results = await asyncio.gather(*(_outpaint_one(client, u) for u in urls))
    return list(results)
