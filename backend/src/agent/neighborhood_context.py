"""Google Places nearby venues + Hera-hosted reference images for renders.

Geocodes the listing, searches nearby POIs by ICP-tuned place types, downloads
Place Photos, uploads each to ``POST /files`` so Hera receives stable HTTPS
URLs. When ``GOOGLE_PLACES_API_KEY`` (or ``GOOGLE_MAPS_API_KEY``) is unset or
any step fails, returns an empty context — the pipeline continues unchanged.
"""

from __future__ import annotations

import asyncio
import math
import os
from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx

from src.agent.models import ScrapedListing
from src.logger import log

_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"
_HERA_FILES_URL = "https://api.hera.video/v1/files"

# Nearby Search accepts one ``type`` per request (Table 1 types).
_PERSONA_PLACE_TYPES: dict[str, list[str]] = {
    "Luxury experience seeker": ["spa", "art_gallery", "tourist_attraction", "shopping_mall"],
    "Family visiting adult child": ["park", "zoo", "museum", "tourist_attraction"],
    "Friend group celebration": ["night_club", "bar", "tourist_attraction", "cafe"],
    "Party group": ["night_club", "bar", "tourist_attraction"],
    "Digital nomad": ["cafe", "library", "park", "tourist_attraction"],
    "First-time city tourist": ["tourist_attraction", "museum", "park", "cafe"],
    "Couples weekend break": ["park", "cafe", "art_gallery", "tourist_attraction"],
    "Solo traveler": ["cafe", "park", "library", "tourist_attraction"],
    "Budget-smart traveler": ["park", "cafe", "tourist_attraction"],
}

_DEFAULT_TYPES = ["cafe", "park", "tourist_attraction", "museum"]

_MAX_PLACES = 3
_MAX_TYPES_QUERIED = 4
_NEARBY_RADIUS_M = 2000
_PHOTO_MAX_WIDTH = 1200
_HTTP_TIMEOUT = 25.0


def _places_api_key() -> str | None:
    return os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY") or None


def _hera_api_key() -> str | None:
    raw = os.getenv("HERA_API_KEY", "")
    return raw if raw.strip() else None


def _persona_from_icp(icp: Mapping[str, Any] | None) -> str:
    if not isinstance(icp, Mapping):
        return ""
    best = icp.get("best_icp")
    if not isinstance(best, Mapping):
        return ""
    p = best.get("persona")
    return p.strip() if isinstance(p, str) else ""


def _place_types_for_persona(persona: str) -> list[str]:
    types = _PERSONA_PLACE_TYPES.get(persona, _DEFAULT_TYPES)
    out: list[str] = []
    seen: set[str] = set()
    for t in types:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:_MAX_TYPES_QUERIED]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _score_candidate(
    rating: float | None,
    user_ratings_total: int | None,
    distance_m: float,
) -> float:
    r = float(rating) if rating is not None else 4.0
    n = int(user_ratings_total) if user_ratings_total else 0
    trust = math.log1p(max(n, 1))
    dist_pen = 1.0 + (distance_m / 400.0)
    return (r * trust) / dist_pen


@dataclass
class NeighborhoodContext:
    """Serializable result for ``AgentDecision`` + optional LLM enrichment rows."""

    places: list[dict[str, Any]] = field(default_factory=list)
    nearby_places_verified: list[dict[str, Any]] = field(default_factory=list)
    hera_reference_urls: list[str] = field(default_factory=list)

    @staticmethod
    def empty() -> NeighborhoodContext:
        return NeighborhoodContext()


async def _geocode(client: httpx.AsyncClient, address: str, key: str) -> tuple[float, float] | None:
    r = await client.get(_GEOCODE_URL, params={"address": address, "key": key})
    r.raise_for_status()
    data = r.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        log.warning("neighborhood: geocode status=%s", data.get("status"))
    results = data.get("results") or []
    if not results:
        return None
    loc = (results[0].get("geometry") or {}).get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return float(lat), float(lng)
    return None


async def _nearby_for_type(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    place_type: str,
    key: str,
) -> list[dict[str, Any]]:
    params = {
        "location": f"{lat},{lng}",
        "radius": _NEARBY_RADIUS_M,
        "type": place_type,
        "key": key,
    }
    r = await client.get(_NEARBY_URL, params=params)
    r.raise_for_status()
    data = r.json()
    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        log.warning("neighborhood: nearby type=%s status=%s", place_type, status)
    return list(data.get("results") or [])


async def _download_place_photo(
    client: httpx.AsyncClient,
    photo_reference: str,
    key: str,
) -> bytes | None:
    params = {"maxwidth": _PHOTO_MAX_WIDTH, "photo_reference": photo_reference, "key": key}
    r = await client.get(_PHOTO_URL, params=params, follow_redirects=True)
    if r.status_code >= 400:
        log.warning("neighborhood: photo HTTP %s", r.status_code)
        return None
    if len(r.content) < 256:
        return None
    return r.content


async def _upload_hera_file(client: httpx.AsyncClient, hera_key: str, data: bytes, filename: str) -> str | None:
    try:
        r = await client.post(
            _HERA_FILES_URL,
            headers={"x-api-key": hera_key},
            files={"file": (filename, data, "image/jpeg")},
            timeout=_HTTP_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        log.warning("neighborhood: Hera upload failed: %s", exc)
        return None
    if r.status_code >= 400:
        log.warning("neighborhood: Hera files HTTP %s %s", r.status_code, r.text[:200])
        return None
    try:
        payload = r.json()
    except ValueError:
        return None
    url = payload.get("url")
    return url if isinstance(url, str) and url.startswith("http") else None


async def _resolve_place(
    client: httpx.AsyncClient,
    i: int,
    row: dict[str, Any],
    dist_m: float,
    gkey: str,
    hkey: str,
) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    """Download + upload one place's hero photo. Returns (place_row, verified_row,
    hera_url) on success, None on any soft failure (missing fields, download or
    upload miss). Designed to be safely run via asyncio.gather alongside peers."""
    name = row.get("name")
    if not isinstance(name, str):
        return None
    photos = row.get("photos") or []
    pref_obj = photos[0] if photos else {}
    pref = pref_obj.get("photo_reference") if isinstance(pref_obj, dict) else None
    if not isinstance(pref, str):
        return None
    html_attr = pref_obj.get("html_attributions") if isinstance(pref_obj, dict) else None
    attr_list: list[str] = []
    if isinstance(html_attr, list):
        attr_list = [a for a in html_attr if isinstance(a, str)]

    img = await _download_place_photo(client, pref, gkey)
    if not img:
        return None
    url = await _upload_hera_file(client, hkey, img, f"nearby-{i}.jpg")
    if not url:
        return None

    types_list = row.get("types") or []
    tlist = [t for t in types_list if isinstance(t, str)][:8]
    vicinity = row.get("vicinity")
    vstr = vicinity if isinstance(vicinity, str) else None
    rating = row.get("rating")
    r_out = float(rating) if isinstance(rating, (int, float)) else None
    dist_int = int(round(dist_m))

    place_row = {
        "name": name,
        "distance_m": dist_int,
        "types": tlist,
        "rating": r_out,
        "vicinity": vstr,
        "google_photo_attributions": attr_list,
    }
    verified_row = {
        "index": i,
        "name": name,
        "types": tlist,
        "distance_m": dist_int,
        "rating": r_out,
        "vicinity": vstr,
        "hera_reference_url": url,
        "google_photo_attributions": attr_list,
    }
    return place_row, verified_row, url


async def fetch_neighborhood_context(
    listing: ScrapedListing,
    icp: Mapping[str, Any] | None,
) -> NeighborhoodContext:
    """Best-effort nearby POIs + Hera URLs. Empty when APIs or uploads fail."""
    gkey = _places_api_key()
    hkey = _hera_api_key()
    if not gkey:
        return NeighborhoodContext.empty()
    if not hkey:
        log.warning("neighborhood: HERA_API_KEY missing — skip place photo uploads")
        return NeighborhoodContext.empty()

    address = f"{listing.title}, {listing.location}".strip()[:280] or listing.location
    persona = _persona_from_icp(icp)
    types = _place_types_for_persona(persona)

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            geo = await _geocode(client, address, gkey)
            if geo is None:
                log.info("neighborhood: geocode miss for %r", address[:80])
                return NeighborhoodContext.empty()
            lat0, lng0 = geo

            nearby_lists = await asyncio.gather(
                *[_nearby_for_type(client, lat0, lng0, t, gkey) for t in types]
            )

            merged: dict[str, dict[str, Any]] = {}
            for block in nearby_lists:
                for row in block:
                    pid = row.get("place_id")
                    if not isinstance(pid, str) or pid in merged:
                        continue
                    merged[pid] = row

            scored: list[tuple[float, dict[str, Any], float]] = []
            for row in merged.values():
                loc = (row.get("geometry") or {}).get("location") or {}
                plat, plng = loc.get("lat"), loc.get("lng")
                if not isinstance(plat, (int, float)) or not isinstance(plng, (int, float)):
                    continue
                dist = _haversine_m(lat0, lng0, float(plat), float(plng))
                rating = row.get("rating")
                rfloat = float(rating) if isinstance(rating, (int, float)) else None
                urt = row.get("user_ratings_total")
                nrat = int(urt) if isinstance(urt, int) else None
                photos = row.get("photos") or []
                if not isinstance(photos, list) or not photos:
                    continue
                pref = (photos[0] or {}).get("photo_reference")
                if not isinstance(pref, str):
                    continue
                sc = _score_candidate(rfloat, nrat, dist)
                scored.append((sc, row, dist))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:_MAX_PLACES]

            # Run download + upload per place in parallel. Sequential previously
            # added 3× the slowest Hera upload to phase 2, which dominated the
            # tail when /files was congested. Parallel: tail = max(slowest), not
            # sum. Failures still soft-skip individual places.
            results = await asyncio.gather(
                *[
                    _resolve_place(client, i, row, dist_m, gkey, hkey)
                    for i, (_sc, row, dist_m) in enumerate(top, start=1)
                ],
                return_exceptions=False,
            )

            places_out: list[dict[str, Any]] = []
            verified: list[dict[str, Any]] = []
            hera_urls: list[str] = []
            for resolved in results:
                if resolved is None:
                    continue
                place_row, verified_row, url = resolved
                places_out.append(place_row)
                verified.append(verified_row)
                hera_urls.append(url)

            if not places_out:
                return NeighborhoodContext.empty()

            log.info(
                "neighborhood: ok persona=%r places=%d place_types=%s",
                persona or "(default)",
                len(places_out),
                types,
            )
            return NeighborhoodContext(
                places=places_out,
                nearby_places_verified=verified,
                hera_reference_urls=hera_urls,
            )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        log.warning("neighborhood: failed: %s", exc)
        return NeighborhoodContext.empty()
