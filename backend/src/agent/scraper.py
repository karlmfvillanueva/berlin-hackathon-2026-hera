"""Live Airbnb listing scraper (Phase 2, behind ENABLE_LIVE_SCRAPE).

Strategy (best-first):
  1. JSON-LD (`script[type="application/ld+json"]` with @type=VacationRental/Product)
     — Airbnb ships a full structured payload here: name, description, address,
     image[], aggregateRating, lat/long. Most reliable and stable across regions.
  2. OpenGraph tags (`og:title`, `og:description`, `og:image`) — backfills any
     gaps and carries useful "1 Schlafzimmer · 1 Bett" style metadata in og:title.
  3. Visible DOM selectors — last-ditch fallback for the photo gallery, mirrors
     `backend/scripts/probe_scrape.py`.

Returns None on any failure path → caller raises 503 scrape_blocked, never 500.
The fixture loader stays the default; live scraping is opt-in for the demo.
"""

from __future__ import annotations

import json
import re

from playwright.async_api import Page, async_playwright

from src.agent.models import Photo, ScrapedListing
from src.logger import log

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_NAV_TIMEOUT_MS = 30_000
_SETTLE_MS = 4_000


async def scrape_listing(url: str) -> ScrapedListing | None:
    """Headless scrape. Returns None on every failure path."""
    log.info("scraper: starting url=%s", url)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
                await page.wait_for_timeout(_SETTLE_MS)

                if "/rooms/" not in page.url:
                    log.warning(
                        "scraper: redirected off listing url=%s final=%s", url, page.url
                    )
                    return None

                ld = await _read_json_ld(page)
                og = await _read_og_tags(page)
                dom_photos = await _read_dom_photos(page)

                listing = _assemble(url, ld, og, dom_photos)
                if listing is None:
                    log.warning("scraper: could not assemble listing url=%s", url)
                    return None

                log.info(
                    "scraper: ok title=%r photos=%d desc_chars=%d",
                    listing.title[:60],
                    len(listing.photos),
                    len(listing.description),
                )
                return listing
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:
        log.exception("scraper: failed url=%s reason=%s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------


async def _read_json_ld(page: Page) -> dict | None:
    """Return the first VacationRental/Product JSON-LD payload, or None."""
    try:
        scripts = await page.locator('script[type="application/ld+json"]').all()
    except Exception:
        return None
    for s in scripts:
        try:
            text = await s.text_content()
            if not text:
                continue
            data = json.loads(text)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("@type") in {"VacationRental", "Product", "LodgingBusiness"}:
            return data
    return None


async def _read_og_tags(page: Page) -> dict[str, str]:
    """Pull og:title / og:description / og:image. Empty dict on full miss."""
    out: dict[str, str] = {}
    for prop in ("og:title", "og:description", "og:image"):
        try:
            loc = page.locator(f'meta[property="{prop}"]')
            if await loc.count():
                v = await loc.get_attribute("content")
                if v:
                    out[prop] = v
        except Exception:
            continue
    return out


async def _read_dom_photos(page: Page) -> list[str]:
    """DOM photo fallback — first 12 listing-image-looking URLs."""
    urls: list[str] = []
    try:
        loc = page.locator("picture img, img[data-original-uri]")
        count = await loc.count()
        for i in range(min(count, 30)):
            src = await loc.nth(i).get_attribute("src")
            if src and _looks_like_listing_photo(src) and src not in urls:
                urls.append(src)
                if len(urls) >= 12:
                    break
    except Exception:
        pass
    return urls


# ---------------------------------------------------------------------------
# Assembly + helpers
# ---------------------------------------------------------------------------


def _assemble(
    url: str,
    ld: dict | None,
    og: dict[str, str],
    dom_photos: list[str],
) -> ScrapedListing | None:
    """Merge JSON-LD + og:tags + DOM photos into a ScrapedListing.

    Requires at minimum: a non-empty title and at least 1 photo. Otherwise None.
    """
    og_title = (og.get("og:title") or "").strip()
    title = _clean_title(
        (ld.get("name") if ld else None)
        or og_title
        or ""
    )

    description = ""
    if ld and isinstance(ld.get("description"), str):
        description = ld["description"].strip()
    if not description and og.get("og:description"):
        description = og["og:description"].strip()

    location = ""
    if ld and isinstance(ld.get("address"), dict):
        loc = ld["address"].get("addressLocality") or ld["address"].get("addressRegion")
        if isinstance(loc, str):
            location = loc.strip()
    if not location and og_title:
        # og:title pattern: "Eigentumswohnung · Paris · ★4,94 · 1 Schlafzimmer ..."
        parts = [p.strip() for p in og_title.split("·") if p.strip()]
        if len(parts) >= 2:
            location = parts[1]

    bedrooms_sleeps = _parse_bedrooms_sleeps(og_title)

    photos: list[Photo] = []
    if ld:
        for img in (ld.get("image") or []):
            if isinstance(img, str):
                img_url = img
            elif isinstance(img, dict):
                img_url = img.get("url")
            else:
                img_url = None
            if isinstance(img_url, str) and _looks_like_listing_photo(img_url):
                photos.append(Photo(url=img_url, label=None))
    # Add DOM photos as supplement (deduped)
    seen = {p.url for p in photos}
    for u in dom_photos:
        if u not in seen:
            photos.append(Photo(url=u, label=None))
            seen.add(u)
    # Fall back to og:image as a single hero if everything else is empty
    if not photos and og.get("og:image"):
        photos.append(Photo(url=og["og:image"], label=None))

    if not title or not photos:
        return None

    rating = _format_rating(ld) if ld else ""

    return ScrapedListing(
        url=url,
        title=title,
        description=description,
        amenities=[],  # JSON-LD rarely lists these reliably; skip for now
        photos=photos[:10],
        location=location,
        price_display=rating,  # repurpose: show rating since price isn't in JSON-LD
        bedrooms_sleeps=bedrooms_sleeps,
    )


def _clean_title(title: str) -> str:
    """Strip Airbnb's site-wide suffixes from the page title."""
    t = title.strip()
    # Page-title suffixes seen in og:title vary by locale ("- Airbnb", "| Airbnb")
    for sep in (" - Airbnb", " | Airbnb"):
        if sep in t:
            t = t.split(sep)[0].strip()
            break
    return t


def _parse_bedrooms_sleeps(og_title: str) -> str:
    """Extract bedrooms / beds / baths blob from og:title.

    og:title example:
      'Eigentumswohnung · Paris · ★4,94 · 1 Schlafzimmer · 1 Bett · 1 Gemeinschafts-Badezimmer'
    Returns the joined "X Y · X Z · X W" sequence or '' if not found.
    """
    if not og_title:
        return ""
    parts = [p.strip() for p in og_title.split("·") if p.strip()]
    keywords = re.compile(
        r"(schlafzimmer|bedroom|bett|bed|bad|bath|sleeps|gäste|guests)",
        re.IGNORECASE,
    )
    relevant = [p for p in parts if keywords.search(p)]
    return " · ".join(relevant) if relevant else ""


def _format_rating(ld: dict) -> str:
    """Format aggregateRating as 'rating★ (count reviews)' or ''."""
    agg = ld.get("aggregateRating")
    if not isinstance(agg, dict):
        return ""
    rv = agg.get("ratingValue")
    rc = agg.get("ratingCount")
    if rv is None:
        return ""
    if rc:
        return f"{rv}★ ({rc} reviews)"
    return f"{rv}★"


def _looks_like_listing_photo(src: str) -> bool:
    """Filter avatars, badges, platform assets — keep only listing photos."""
    if not src.startswith("http"):
        return False
    if "muscache.com" not in src:
        return True  # other CDNs slip through; better to keep than drop
    # Drop user avatars and platform-asset badges (e.g. GuestFavorite icon)
    if "/user/" in src or "platform-assets" in src.lower():
        return False
    return True
