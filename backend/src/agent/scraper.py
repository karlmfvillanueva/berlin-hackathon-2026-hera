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
import os
import re

import httpx
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

_SCRAPERAPI_URL = "https://api.scraperapi.com/"
_SCRAPERAPI_TIMEOUT_S = 90.0  # ultra_premium can take 30–60 s; give headroom


async def scrape_listing(url: str) -> ScrapedListing | None:
    """Live scrape with two-tier strategy:
      1. Direct Playwright from this container's IP (fast, free, but Airbnb
         blocks Railway-class datacenter IPs via Cloudflare/PerimeterX).
      2. ScraperAPI fallback — they render the page from a residential proxy
         pool, return the rendered HTML, we feed it back into Playwright's
         `set_content()` so the existing JSON-LD/OG/DOM extractors stay reused.

    Returns None on every failure path so the caller raises 503, never 500.
    """
    log.info("scraper: starting url=%s", url)
    listing = await _scrape_via_playwright(url)
    if listing is not None:
        return listing

    if os.getenv("SCRAPERAPI_KEY"):
        log.info("scraper: playwright miss → ScraperAPI fallback url=%s", url)
        return await _scrape_via_scraperapi(url)

    log.info("scraper: playwright miss + no SCRAPERAPI_KEY → giving up url=%s", url)
    return None


async def _scrape_via_playwright(url: str) -> ScrapedListing | None:
    """Direct Playwright path. None on any failure (timeout, anti-bot, parse)."""
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
                        "playwright: redirected off listing url=%s final=%s", url, page.url
                    )
                    return None

                listing = await _extract_from_page(page, url)
                if listing is None:
                    log.warning("playwright: could not assemble listing url=%s", url)
                    return None

                _log_listing("playwright", listing)
                return listing
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:
        log.exception("playwright: failed url=%s reason=%s", url, exc)
        return None


async def _scrape_via_scraperapi(url: str) -> ScrapedListing | None:
    """ScraperAPI fallback. Fetches rendered HTML via their proxy pool, then
    re-uses the same Playwright-based extractors via `page.set_content()`.

    Airbnb is anti-bot-hardened, so we always pass `ultra_premium=true` —
    that's expensive (30 credits/req), but standard premium misses ~all the
    time on listing pages."""
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        return None

    params = {
        "api_key": api_key,
        "url": url,
        "render": "true",
        "ultra_premium": "true",
        "country_code": "us",
    }
    try:
        async with httpx.AsyncClient(timeout=_SCRAPERAPI_TIMEOUT_S) as client:
            r = await client.get(_SCRAPERAPI_URL, params=params)
    except Exception as exc:
        log.exception("scraperapi: request failed url=%s reason=%s", url, exc)
        return None

    if r.status_code != 200:
        log.warning("scraperapi: %d body=%s url=%s", r.status_code, r.text[:200], url)
        return None

    html = r.text
    if not html or "/rooms/" not in r.text and "VacationRental" not in r.text:
        log.warning("scraperapi: response looks empty/blocked url=%s len=%d", url, len(html))
        return None

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
                await page.set_content(html, wait_until="domcontentloaded")
                listing = await _extract_from_page(page, url)
                if listing is None:
                    log.warning("scraperapi: could not assemble listing url=%s", url)
                    return None

                _log_listing("scraperapi", listing)
                return listing
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:
        log.exception("scraperapi: parse failed url=%s reason=%s", url, exc)
        return None


async def _extract_from_page(page: Page, url: str) -> ScrapedListing | None:
    """Run all extractors against a loaded Page (regardless of source) and
    assemble. Centralised so Playwright + ScraperAPI paths stay symmetric."""
    ld = await _read_json_ld(page)
    og = await _read_og_tags(page)
    dom_photos = await _read_dom_photos(page)
    review_quotes = await _read_review_quotes(page)
    review_tags = await _read_review_tags(page)
    return _assemble(url, ld, og, dom_photos, review_quotes, review_tags)


def _log_listing(source: str, listing: ScrapedListing) -> None:
    log.info(
        "%s: ok title=%r photos=%d desc_chars=%d "
        "review_quotes=%d review_tags=%d rating=%s reviews_count=%s",
        source,
        listing.title[:60],
        len(listing.photos),
        len(listing.description),
        len(listing.review_quotes),
        len(listing.review_tags),
        listing.rating_overall,
        listing.reviews_count,
    )


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


async def _read_review_quotes(page: Page, max_n: int = 6) -> list[str]:
    """Best-effort: extract up to N verbatim guest review quotes from the DOM.

    Reviews are lazy-loaded; we try to scroll the reviews section into view
    first. Selectors try several patterns because Airbnb's React DOM is
    obfuscated — the `[lang]` attribute on review text is the most stable
    signal because it's used for translation/accessibility. Returns whatever
    we find, empty list on full miss. The Reviews Evaluation agent already
    handles sparse / empty input gracefully.
    """
    try:
        await page.locator(
            '[data-section-id*="REVIEWS"], [data-pageid*="reviews"]'
        ).first.scroll_into_view_if_needed(timeout=5000)
        await page.wait_for_timeout(800)
    except Exception:
        pass

    quotes: list[str] = []
    seen: set[str] = set()
    selector_candidates = (
        '[data-review-id] span[lang]',
        '[data-section-id*="REVIEWS"] span[lang]',
        '[data-pageid*="reviews"] span[lang]',
        'div[role="article"] span[lang]',
    )
    for selector in selector_candidates:
        try:
            loc = page.locator(selector)
            count = await loc.count()
        except Exception:
            continue
        for i in range(min(count, 30)):
            try:
                text = await loc.nth(i).text_content()
            except Exception:
                continue
            if not text:
                continue
            cleaned = text.strip()
            # Real reviews are 30–500 chars; below = UI noise, above = the
            # "show translation" trailing block bleeding into another node.
            if not (30 <= len(cleaned) <= 500):
                continue
            # Cap at 280 chars: long quotes don't fit short-form video text.
            cleaned = cleaned[:280]
            if cleaned in seen:
                continue
            seen.add(cleaned)
            quotes.append(cleaned)
            if len(quotes) >= max_n:
                return quotes
        if quotes:
            # Selector worked — stop trying others.
            return quotes
    return quotes


async def _read_review_tags(page: Page, max_n: int = 8) -> list[str]:
    """Best-effort: extract review category labels (Cleanliness, Communication,
    Location, …) and any review-tag pills. Returns short 1–3-word strings.
    """
    tags: list[str] = []
    seen: set[str] = set()
    selector_candidates = (
        '[data-testid*="review-tag"]',
        '[data-section-id*="REVIEWS"] button[type="button"] span',
    )
    for selector in selector_candidates:
        try:
            loc = page.locator(selector)
            count = await loc.count()
        except Exception:
            continue
        for i in range(min(count, 30)):
            try:
                text = await loc.nth(i).text_content()
            except Exception:
                continue
            if not text:
                continue
            cleaned = text.strip()
            words = cleaned.split()
            # Filter to plausible tag pills: 1–3 words, alphabetic-ish.
            if not (1 <= len(words) <= 3) or len(cleaned) > 32:
                continue
            if not any(c.isalpha() for c in cleaned):
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            tags.append(cleaned)
            if len(tags) >= max_n:
                return tags
        if tags:
            return tags
    return tags


def _extract_rating_stats(ld: dict | None) -> tuple[float | None, int | None]:
    """Pull (rating_overall, reviews_count) from JSON-LD aggregateRating.

    Both fields are optional; returns (None, None) on full miss.
    """
    if not isinstance(ld, dict):
        return (None, None)
    agg = ld.get("aggregateRating")
    if not isinstance(agg, dict):
        return (None, None)
    rating: float | None = None
    count: int | None = None
    rv = agg.get("ratingValue")
    if isinstance(rv, (int, float)):
        rating = float(rv)
    elif isinstance(rv, str):
        # Locales sometimes use a comma decimal separator: "4,94".
        try:
            rating = float(rv.replace(",", "."))
        except ValueError:
            rating = None
    rc = agg.get("ratingCount") or agg.get("reviewCount")
    if isinstance(rc, int):
        count = rc
    elif isinstance(rc, str) and rc.isdigit():
        count = int(rc)
    return (rating, count)


# ---------------------------------------------------------------------------
# Assembly + helpers
# ---------------------------------------------------------------------------


def _assemble(
    url: str,
    ld: dict | None,
    og: dict[str, str],
    dom_photos: list[str],
    review_quotes: list[str] | None = None,
    review_tags: list[str] | None = None,
) -> ScrapedListing | None:
    """Merge JSON-LD + og:tags + DOM photos + review extracts into a ScrapedListing.

    Requires at minimum: a non-empty title and at least 1 photo. Otherwise None.
    """
    og_title = (og.get("og:title") or "").strip()
    title = _clean_title((ld.get("name") if ld else None) or og_title or "")

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
        for img in ld.get("image") or []:
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

    rating_display = _format_rating(ld) if ld else ""
    rating_overall, reviews_count = _extract_rating_stats(ld)

    return ScrapedListing(
        url=url,
        title=title,
        description=description,
        amenities=[],  # JSON-LD rarely lists these reliably; skip for now
        photos=photos[:10],
        location=location,
        # `price_display` continues to surface the rating string for the
        # frontend (price isn't reliably in JSON-LD); structured rating /
        # review fields go to their semantic homes for the agent layer.
        price_display=rating_display,
        bedrooms_sleeps=bedrooms_sleeps,
        rating_overall=rating_overall,
        reviews_count=reviews_count,
        review_quotes=list(review_quotes or []),
        review_tags=list(review_tags or []),
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
