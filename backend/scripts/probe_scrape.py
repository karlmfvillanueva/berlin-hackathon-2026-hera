"""Airbnb scrape probe.

Tests whether Playwright can extract the fields the agent needs from a live listing:
title, description, amenities, photo URLs, location. Reports presence/absence per field
and surfaces anti-bot blocking signals (login walls, captchas, blank pages).

Run:
    cd backend && uv run python scripts/probe_scrape.py [URL ...]

Defaults to a few Berlin listings. Swap in your own URLs if these are stale.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field

from playwright.async_api import async_playwright

# --- Config ---
HEADLESS = False  # show the browser so Karl can watch
NAV_TIMEOUT_MS = 30_000
SETTLE_MS = 4_000  # wait after load for client-side rendering

DEFAULT_URLS = [
    "https://www.airbnb.com/rooms/19278160",
    "https://www.airbnb.com/rooms/45605768",
    "https://www.airbnb.com/rooms/52047810",
]


@dataclass
class ScrapeReport:
    url: str
    final_url: str = ""
    title: str | None = None
    description_snippet: str | None = None
    amenity_count: int = 0
    photo_count: int = 0
    location_text: str | None = None
    blocked_signals: list[str] = field(default_factory=list)
    error: str | None = None

    def verdict(self) -> str:
        if self.error:
            return f"ERROR: {self.error}"
        if self.blocked_signals:
            return f"BLOCKED ({', '.join(self.blocked_signals)})"
        missing = []
        if not self.title:
            missing.append("title")
        if not self.description_snippet:
            missing.append("description")
        if self.photo_count < 3:
            missing.append(f"photos<3 ({self.photo_count})")
        if missing:
            return f"PARTIAL (missing: {', '.join(missing)})"
        return "OK"


async def probe_one(url: str) -> ScrapeReport:
    report = ScrapeReport(url=url)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            await page.wait_for_timeout(SETTLE_MS)
            report.final_url = page.url

            # Visible-element checks only -- substring matching on full HTML
            # false-positives on every page (Airbnb embeds reCAPTCHA scripts site-wide).
            captcha_selector = (
                'iframe[title*="captcha" i], iframe[src*="recaptcha/api2/anchor"]'
            )
            try:
                if await page.locator(captcha_selector).count():
                    report.blocked_signals.append("captcha")
            except Exception:
                pass

            # Detect redirect to a non-listing page (homepage or error).
            if "/rooms/" not in page.url:
                report.blocked_signals.append("redirected_off_listing")

            try:
                title = (await page.title()).strip()
                report.title = title or None
                generic_titles = {
                    "airbnb",
                    (
                        "airbnb: vacation rentals, cabins, beach houses, "
                        "unique homes & experiences"
                    ),
                }
                if title.lower() in generic_titles:
                    report.blocked_signals.append("generic_homepage_title")
            except Exception:
                pass

            try:
                meta = await page.locator('meta[name="description"]').get_attribute("content")
                if meta:
                    report.description_snippet = meta[:160]
            except Exception:
                pass

            try:
                amenities = await page.locator(
                    'div[data-section-id*="AMENITIES"] li, '
                    'section[aria-labelledby*="amenities"] li'
                ).count()
                report.amenity_count = amenities
            except Exception:
                pass

            try:
                photos = await page.locator('picture img, img[data-original-uri]').count()
                report.photo_count = photos
            except Exception:
                pass

            try:
                loc_el = page.locator('button[data-section-id*="LOCATION"], a[href*="/maps/"]')
                if await loc_el.count():
                    report.location_text = (await loc_el.first.inner_text())[:120].strip()
            except Exception:
                pass

        except Exception as exc:
            report.error = type(exc).__name__ + ": " + str(exc)[:200]
        finally:
            await context.close()
            await browser.close()
    return report


async def main(urls: list[str]) -> int:
    print(f"Probing {len(urls)} listing(s) with HEADLESS={HEADLESS}\n")
    reports: list[ScrapeReport] = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        rep = await probe_one(url)
        reports.append(rep)
        print(f"    verdict: {rep.verdict()}")
        print(f"    final_url: {rep.final_url}")
        print(f"    title: {(rep.title or '')[:80]}")
        print(f"    desc:  {(rep.description_snippet or '')[:80]}")
        print(f"    amenities={rep.amenity_count}  photos={rep.photo_count}")
        if rep.location_text:
            print(f"    location: {rep.location_text}")
        print()

    ok = sum(1 for r in reports if r.verdict() == "OK")
    print("=" * 60)
    print(f"OK: {ok}/{len(reports)}")
    if ok == 0:
        print("VERDICT: Scraping unviable as-is. Plan for JSON fixtures fallback.")
        return 1
    if ok < len(reports):
        print("VERDICT: Partial. Some listings scrape; need URL pre-flight before demo.")
        return 0
    print("VERDICT: Scraping viable. Proceed with Playwright in production path.")
    return 0


if __name__ == "__main__":
    cli_urls = sys.argv[1:] or DEFAULT_URLS
    sys.exit(asyncio.run(main(cli_urls)))
