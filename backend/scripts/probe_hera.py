"""Hera latency probe.

Submits a short 9:16 video, polls until success/failed, prints wall time.
Determines whether the hackathon demo can be live-generated or must be pre-rendered.

Run:
    cd backend && uv run python scripts/probe_hera.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# --- Config ---
REPO_ROOT = Path(__file__).resolve().parents[2]
CREDS_FILE = REPO_ROOT / "credentials" / "credentials.env"

HERA_BASE_URL = "https://api.hera.video/v1"
POLL_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 600  # 10-minute hard cap

PROBE_PROMPT = (
    "Create a 15-second vertical motion graphics video for an Airbnb listing. "
    "Angle: City Escape. "
    "Hook (0-3s): rooftop reveal of a Berlin loft at golden hour. "
    "Middle (3-12s): interior cuts highlighting natural light, exposed brick, modern kitchen. "
    "Close (12-15s): pull-back shot with end card 'BERLIN LOFT'. "
    "Style: clean, modern, warm tones."
)

PROBE_BODY = {
    "prompt": PROBE_PROMPT,
    "duration_seconds": 15,
    "outputs": [
        {
            "format": "mp4",
            "aspect_ratio": "9:16",
            "fps": "30",
            "resolution": "1080p",
        }
    ],
}


def main() -> int:
    load_dotenv(dotenv_path=CREDS_FILE)
    api_key = os.getenv("HERA_API_KEY", "")
    if not api_key:
        print(f"ERROR: HERA_API_KEY not found in {CREDS_FILE}", file=sys.stderr)
        return 1

    print(f"Loaded credentials from {CREDS_FILE.relative_to(REPO_ROOT)}")
    print(f"Probe target: {HERA_BASE_URL}")
    print(f"Format: 9:16, 15s, 1080p, mp4")
    print()

    headers = {"x-api-key": api_key, "content-type": "application/json"}
    t_submit_start = time.monotonic()

    with httpx.Client(base_url=HERA_BASE_URL, headers=headers, timeout=60.0) as client:
        print(f"[{_elapsed(t_submit_start):>6}s] POST /videos ...")
        try:
            r = client.post("/videos", json=PROBE_BODY)
        except httpx.HTTPError as exc:
            print(f"FAILED: request error: {exc}", file=sys.stderr)
            return 2

        if r.status_code >= 400:
            print(f"FAILED: HTTP {r.status_code} -> {r.text[:500]}", file=sys.stderr)
            return 3

        body = r.json()
        video_id = body.get("video_id")
        project_url = body.get("project_url")
        if not video_id:
            print(f"FAILED: response missing video_id: {body}", file=sys.stderr)
            return 4

        t_submit_end = time.monotonic()
        submit_seconds = t_submit_end - t_submit_start
        print(f"[{_elapsed(t_submit_start):>6}s] submitted in {submit_seconds:.2f}s")
        print(f"           video_id={video_id}")
        if project_url:
            print(f"           project_url={project_url}")
        print()

        deadline = t_submit_end + MAX_WAIT_SECONDS
        last_status = None
        while True:
            now = time.monotonic()
            if now > deadline:
                print(
                    f"\nTIMEOUT: still in-progress after {MAX_WAIT_SECONDS}s "
                    f"-- demo must be pre-rendered.",
                    file=sys.stderr,
                )
                return 5

            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                r = client.get(f"/videos/{video_id}")
            except httpx.HTTPError as exc:
                print(f"  poll error (continuing): {exc}", file=sys.stderr)
                continue

            if r.status_code >= 400:
                print(f"  poll HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
                continue

            body = r.json()
            status = body.get("status")
            if status != last_status:
                print(f"[{_elapsed(t_submit_start):>6}s] status={status}")
                last_status = status

            if status == "success":
                total_seconds = time.monotonic() - t_submit_start
                outputs = body.get("outputs") or []
                file_url = outputs[0].get("file_url") if outputs else None
                print()
                print("=" * 60)
                print(f"SUCCESS in {total_seconds:.1f}s wall time")
                print("=" * 60)
                print(f"file_url: {file_url}")
                _verdict(total_seconds)
                return 0

            if status == "failed":
                total_seconds = time.monotonic() - t_submit_start
                print(f"\nFAILED after {total_seconds:.1f}s: {body}", file=sys.stderr)
                return 6


def _elapsed(start: float) -> str:
    return f"{time.monotonic() - start:5.1f}"


def _verdict(seconds: float) -> None:
    print()
    if seconds < 60:
        print("VERDICT: Live demo viable. Generation finishes in well under a minute.")
    elif seconds < 120:
        print("VERDICT: Live demo workable. Fill 60-90s with reasoning narration.")
    elif seconds < 180:
        print("VERDICT: Borderline. Pre-render the demo, show reasoning live.")
    else:
        print("VERDICT: Pre-render required. Generation too slow for stage.")


if __name__ == "__main__":
    sys.exit(main())
