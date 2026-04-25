"""Live Airbnb listing scraper (Phase 2, P2, behind ENABLE_LIVE_SCRAPE).

Strategy:
  1. Try the page's __NEXT_DATA__ blob — full structured listing JSON when present.
  2. Fall back to visible-element CSS selectors (mirrors backend/scripts/probe_scrape.py).
  3. Return None on any failure — caller raises 503 scrape_blocked.

The fixture loader stays the default. Live scraping is opt-in for the demo.
Risk: Airbnb actively blocks scrapers. Failures here should never bubble as 500.
"""

from __future__ import annotations

import json

from playwright.async_api import async_playwright

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
                    log.warning("scraper: redirected off listing url=%s final=%s", url, page.url)
                    return None

                listing = await _extract_from_next_data(page, url)
                if listing is not None:
                    log.info("scraper: extracted via __NEXT_DATA__ photos=%d", len(listing.photos))
                    return listing

                listing = await _extract_from_dom(page, url)
                if listing is not None:
                    log.info("scraper: extracted via DOM fallback photos=%d", len(listing.photos))
                    return listing

                log.warning("scraper: no extraction path succeeded url=%s", url)
                return None
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:
        log.exception("scraper: failed url=%s reason=%s", url, exc)
        return None


async def _extract_from_next_data(page, url: str) -> ScrapedListing | None:
    """Try to pull a ScrapedListing from the page's __NEXT_DATA__ blob.

    Airbnb's internal schema shifts; we look for the title-like 'name' field
    anywhere in the tree as a sanity check, then defer to the DOM extractor
    for everything else. A more thorough mapping is Phase 3 work — for the
    hackathon path the DOM fallback is what actually carries us.
    """
    try:
        raw = await page.eval_on_selector("script#__NEXT_DATA__", "el => el.textContent")
        data = json.loads(raw)
    except Exception:
        return None

    title = _find_first_string(data, key="name", min_len=6, max_len=200)
    if not title:
        return None

    # Title found, but reliable photos/amenities live in the DOM. Return None
    # so the DOM extractor runs and we don't ship an empty listing.
    log.info("scraper: __NEXT_DATA__ title=%r — handing off to DOM extractor", title[:60])
    return None


def _find_first_string(node, key: str, min_len: int, max_len: int) -> str | None:
    """DFS for the first {key: <string>} entry that looks like a real value."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str) and min_len < len(v) < max_len:
                return v
            found = _find_first_string(v, key, min_len, max_len)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_first_string(item, key, min_len, max_len)
            if found:
                return found
    return None


async def _extract_from_dom(page, url: str) -> ScrapedListing | None:
    """DOM-selector fallback. Mirrors backend/scripts/probe_scrape.py findings."""
    try:
        title = (await page.title()).strip()
        if not title or "airbnb" == title.lower():
            return None

        description = ""
        try:
            meta = await page.locator('meta[name="description"]').get_attribute("content")
            description = (meta or "").strip()
        except Exception:
            pass

        amenities: list[str] = []
        try:
            amenity_locator = page.locator(
                'div[data-section-id*="AMENITIES"] li, section[aria-labelledby*="amenities"] li'
            )
            count = await amenity_locator.count()
            for i in range(min(count, 30)):
                text = (await amenity_locator.nth(i).inner_text()).strip()
                if text:
                    amenities.append(text[:80])
        except Exception:
            pass

        photo_urls: list[str] = []
        try:
            img_locator = page.locator("picture img, img[data-original-uri]")
            count = await img_locator.count()
            for i in range(min(count, 20)):
                src = await img_locator.nth(i).get_attribute("src")
                if src and src.startswith("http") and src not in photo_urls:
                    photo_urls.append(src)
        except Exception:
            pass

        if len(photo_urls) < 3:
            return None

        location = ""
        try:
            loc_el = page.locator('button[data-section-id*="LOCATION"], a[href*="/maps/"]')
            if await loc_el.count():
                location = (await loc_el.first.inner_text())[:120].strip()
        except Exception:
            pass

        return ScrapedListing(
            url=url,
            title=title,
            description=description,
            amenities=amenities,
            photos=[Photo(url=u, label=None) for u in photo_urls[:10]],
            location=location,
            price_display="",
            bedrooms_sleeps="",
        )
    except Exception:
        return None
