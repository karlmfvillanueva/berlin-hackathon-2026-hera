"""End-to-end terminal test: /api/listing → /api/generate → poll Hera (demo fixtures).

Uses the same three Airbnb room URLs as the in-app demo picker (see
``fixture_loader.FIXTURES_BY_ROOM_ID``). Requires a **running backend**
(``make dev-backend`` or ``make dev``) and the same ``.env`` as production
(``HERA_API_KEY``, ``GCP_PROJECT`` + ADC, optional Places key).

Auth: omit ``Authorization`` when ``REQUIRE_AUTH=false`` (typical local ``.env``).

Run:
    cd backend && .venv/bin/python scripts/demo_pipeline_terminal.py --demo 1
    cd backend && .venv/bin/python scripts/demo_pipeline_terminal.py --demo 2 --base-url http://127.0.0.1:8000

Options:
    --listing-only   Only POST /api/listing (fast); no Hera job.
    --no-poll        POST /api/generate then exit (print video_id only).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

# Same synthetic URLs as ``main._build_demo_listings`` / fixture map.
DEMO_URLS: dict[str, str] = {
    "1": "https://www.airbnb.com/rooms/648914239689489448",
    "2": "https://www.airbnb.com/rooms/1135417764953008513",
    "3": "https://www.airbnb.com/rooms/1175975083652953434",
}

POLL_INTERVAL_S = 10
POLL_MAX_S = 420


def main() -> None:
    p = argparse.ArgumentParser(description="Terminal demo: listing + generate + poll.")
    p.add_argument(
        "--demo",
        choices=("1", "2", "3"),
        required=True,
        help="Which of the three fixture demos (room IDs 1–3).",
    )
    p.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="FastAPI root (default: http://127.0.0.1:8000).",
    )
    p.add_argument(
        "--listing-only",
        action="store_true",
        help="Stop after Phase 1 listing (no generate, no Hera).",
    )
    p.add_argument(
        "--no-poll",
        action="store_true",
        help="After generate, print video_id and exit without polling Hera.",
    )
    args = p.parse_args()
    base = args.base_url.rstrip("/")
    url = DEMO_URLS[args.demo]

    client = httpx.Client(base_url=base, timeout=600.0)
    # Dev bypass: no Authorization header when REQUIRE_AUTH=false.
    headers = {"content-type": "application/json"}

    print(f"Demo {args.demo}: {url}")
    print(f"POST {base}/api/listing …")

    try:
        lr = client.post(
            "/api/listing",
            headers=headers,
            json={"listing_url": url, "outpaint_enabled": False},
        )
    except httpx.ConnectError as exc:
        print(f"ERROR: cannot connect to {base} — start the backend first.\n{exc}", file=sys.stderr)
        sys.exit(1)

    if lr.status_code >= 400:
        print(lr.text, file=sys.stderr)
        sys.exit(lr.status_code)

    listing_payload = lr.json()
    listing = listing_payload["listing"]
    phase1 = listing_payload["phase1"]
    title = listing.get("title", "")[:60]
    print(f"  OK — listing: {title!r}")

    if args.listing_only:
        print("  (--listing-only) done.")
        sys.exit(0)

    overrides = {
        "language": phase1.get("suggested_language", "en"),
        "tone": phase1.get("suggested_tone", "cozy"),
        "emphasis": [],
        "deemphasis": [],
        "hook_id": "auto",
    }
    gen_body = {
        "listing_url": url,
        "listing": listing,
        "phase1": phase1,
        "overrides": overrides,
    }

    print(f"POST {base}/api/generate … (Phase 2 + Hera; can take 1–4+ minutes)")
    gr = client.post("/api/generate", headers=headers, json=gen_body)
    if gr.status_code >= 400:
        print(gr.text, file=sys.stderr)
        sys.exit(gr.status_code)

    out = gr.json()
    video_id = out["video_id"]
    decision = out.get("decision") or {}
    nb = decision.get("neighborhood_reference_urls") or []
    print(f"  OK — video_id={video_id}")
    print(f"  neighborhood_reference_urls: {len(nb)}")
    if nb:
        for i, u in enumerate(nb, 1):
            print(f"    {i}. {(u[:88] + '…') if len(u) > 88 else u}")

    if args.no_poll:
        print("  (--no-poll) done.")
        sys.exit(0)

    print(f"Polling GET /api/videos/{video_id} every {POLL_INTERVAL_S}s (max {POLL_MAX_S}s)…")
    t0 = time.monotonic()
    while time.monotonic() - t0 < POLL_MAX_S:
        pr = client.get(f"/api/videos/{video_id}", headers=headers)
        if pr.status_code >= 400:
            print(pr.text, file=sys.stderr)
            sys.exit(pr.status_code)
        st = pr.json()
        status = st.get("status")
        outputs = st.get("outputs") or []
        file_url = None
        if outputs:
            file_url = outputs[0].get("file_url")
        print(f"  status={status} file_url={'set' if file_url else 'null'}")
        if status == "success" and file_url:
            print("  DONE — success")
            print(f"  MP4: {file_url}")
            sys.exit(0)
        if status == "failed":
            print("  FAILED", file=sys.stderr)
            print(json.dumps(st, indent=2)[:2000], file=sys.stderr)
            sys.exit(1)
        time.sleep(POLL_INTERVAL_S)

    print("ERROR: poll timeout", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
