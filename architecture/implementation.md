# Phase 2 Implementation Plan — Berlin Hackathon 2026

**What this is:** Ticket plan for Phase 2 of the Airbnb listing video agent. 24-hour hackathon window. Two assignees working in parallel on a layer split.

**Time budget:** 24 hours from kickoff.

**Assignees:**
- Karl — frontend (React/Vite/TS, API client, UI states)
- Joscha — backend (FastAPI, agent modules, Supabase, scraper, outpainter)

**Branch strategy:** `joscha/phase2-backend` and `karl/phase2-frontend` branch from `develop`. Both merge to `develop` at integration points. Final demo runs off `develop`. Do not branch from `main`.

---

## Layer Split Rationale

The file trees for backend (`backend/src/`) and frontend (`frontend/src/`) barely overlap. The only shared seam is the API contract: the Pydantic models in `backend/src/agent/models.py` and their TypeScript mirrors in `frontend/src/types.ts`. Karl owns `frontend/src/types.ts` and Joscha sends type deltas as PR comments or a shared doc, never by editing that file directly. After the contract is locked (Ticket 0, ~1 hour), both can work independently. Karl mocks the backend with hardcoded fixtures; Joscha mocks the frontend with HTTPie/curl. They unblock each other only at the two integration checkpoints (see timeline).

---

## Reality check on the current codebase

The architecture docs describe `AgentDecision` with `angle_id`, `confidence`, `rationale`, and `beliefs_applied`. The shipped codebase uses a different shape: `vibes`, `hook`, `pacing`, `angle`, `background`. These are free-form strings, not the 6-angle taxonomy. The tickets below acknowledge this gap. The contracts in Ticket 0 are what Phase 2 will build toward — they may require migrating or extending the existing model, which is Joscha's call. The key constraint is: Phase 1 frontend must keep working throughout Phase 2 development.

---

## Ticket 0 — API Contract (Shared, Sequential)

**Both owners agree on this before any other ticket starts. Estimated time: 1 hour synchronous.**

### New Pydantic models (Joscha writes, Karl mirrors in TS)

```python
# backend/src/agent/models.py additions / changes

class AgentDecision(BaseModel):
    # Existing Phase 1 fields — keep as-is to avoid breaking Phase 1
    vibes: str
    hook: str
    pacing: str
    angle: str
    background: str
    selected_image_urls: list[str]
    hera_prompt: str
    # Phase 2 additive fields
    outpaint_enabled: bool = False          # were images outpainted?
    beliefs_applied: list[str] = []        # rule_keys that influenced the decision

class ListingRequest(BaseModel):
    listing_url: str
    outpaint_enabled: bool = False          # new — forwarded to pipeline

class RegenerateRequest(BaseModel):
    listing_url: str
    listing: ScrapedListing
    decision: AgentDecision

class RegenerateResponse(BaseModel):
    video_id: str
    decision: AgentDecision
```

### TypeScript mirrors (Karl owns `frontend/src/types.ts`)

```typescript
// frontend/src/types.ts additions

export type AgentDecision = {
  vibes: string;
  hook: string;
  pacing: string;
  angle: string;
  background: string;
  selected_image_urls: string[];
  hera_prompt: string;
  // Phase 2 additive
  outpaint_enabled?: boolean;
  beliefs_applied?: string[];
};
```

### New endpoint shape

```
POST /api/regenerate
Request:  { listing_url: string, listing: ScrapedListing, decision: AgentDecision }
Response: { video_id: string, decision: AgentDecision }
```

The `/api/listing` request body gains `outpaint_enabled: bool` (default `false`). The existing `/api/listing` response shape is unchanged — `outpaint_enabled` in the returned `AgentDecision` tells the frontend whether outpaint ran.

**Contract is locked when:** Joscha has updated `backend/src/agent/models.py` and pushed to his branch. Karl has updated `frontend/src/types.ts` on his branch. Neither modifies the other's file after this point.

---

## Backend Tickets (Joscha)

### B-01 — Wire outpaint flag through listing endpoint

**Owner:** Joscha
**Priority:** P0
**Estimate:** 1h
**Depends on:** Ticket 0
**Files touched:**
- `backend/src/main.py` — update `ListingRequest` import, forward flag to `run()`
- `backend/src/agent/orchestrator.py` — accept `outpaint_enabled` param, pass to future outpainter
- `backend/src/agent/models.py` — already done in Ticket 0

**Acceptance criteria:**
- `POST /api/listing` with `{ "listing_url": "...", "outpaint_enabled": true }` returns 200 with `decision.outpaint_enabled = true`
- `POST /api/listing` with no `outpaint_enabled` field returns 200 with `decision.outpaint_enabled = false` (default)
- Phase 1 behavior (fixture loading, classification) is unchanged
- `backend/logs/app.log` logs `outpaint_enabled=True/False` at INFO level

**Out of scope:** Actual Nanobanana calls (that is B-03). This ticket only threads the flag.

**Implementation notes:** `orchestrator.run()` gains a second parameter `outpaint_enabled: bool = False`. The flag is stored on the returned `AgentDecision`. No conditional logic yet — the outpainter doesn't exist yet.

---

### B-02 — Add `/api/regenerate` endpoint

**Owner:** Joscha
**Priority:** P0
**Estimate:** 1h
**Depends on:** Ticket 0
**Files touched:**
- `backend/src/main.py` — add `POST /api/regenerate` route
- `backend/src/agent/__init__.py` — export `RegenerateRequest`, `RegenerateResponse` if needed

**Acceptance criteria:**
- `POST /api/regenerate` with a valid `RegenerateRequest` body submits a new Hera job and returns `{ video_id, decision }`
- The decision returned is the same decision from the request (no re-classification — regenerate = re-submit same decision)
- Returns `502 hera_unreachable` if Hera is down
- Verified with `http POST :8000/api/regenerate listing_url="..." listing:=@fixture.json decision:=@decision.json`

**Out of scope:** Re-running classification with a new angle (Phase 3). Seeding randomness on Hera side (not exposed in the Hera API currently).

**Implementation notes:** The route is essentially a copy of `POST /api/generate` with a `RegenerateRequest` body. Reuse the same Hera submission logic. The `decision.hera_prompt` and `decision.selected_image_urls` are forwarded as-is.

---

### B-03 — Nanobanana outpainter module

**Owner:** Joscha
**Priority:** P0
**Estimate:** 2h
**Depends on:** B-01
**Files touched:**
- `backend/src/agent/outpainter.py` — new file
- `backend/src/agent/orchestrator.py` — call outpainter when `outpaint_enabled=True`
- `backend/.env.example` (or equivalent) — document `NANOBANANA_API_KEY`

**Acceptance criteria:**
- `outpaint_5_photos(urls: list[str]) -> list[str]` runs 5 Nanobanana calls concurrently via `asyncio.gather`
- Each photo that fails (timeout or API error) falls back to its original URL — the list is always the same length as the input
- Per-photo timeout is 30s (matches architecture doc Layer 4)
- When outpaint is off, `orchestrator.run()` bypasses the outpainter entirely (no latency)
- A fixture-based integration test: pass 1 URL, confirm a URL is returned (original or outpainted)
- `NANOBANANA_API_KEY` is read from env, never hardcoded

**Out of scope:** Aspect ratio detection (use the Nanobanana API's built-in target aspect ratio parameter). Re-uploading to a separate CDN (use Nanobanana's CDN URL directly).

**Implementation notes:** Use the `asyncio.gather` pattern with `return_exceptions=True` so a single photo failure doesn't kill the batch. The Nanobanana API takes a source image URL and a target aspect ratio — see `architecture/02-architecture.md` Layer 4 for the call spec. Use `httpx.AsyncClient` (already a dep) for the API call, not a separate SDK. Call Context7 for the Nanobanana API surface before writing the HTTP call.

**Risk:** Nanobanana API response time at hackathon load is unknown. If per-photo p95 exceeds 30s, the outpaint toggle will be demo-only. Have a fallback fixture with pre-outpainted URLs.

---

### B-04 — Supabase client and schema bootstrap

**Owner:** Joscha
**Priority:** P1
**Estimate:** 1.5h
**Depends on:** none (parallel with B-01)
**Files touched:**
- `backend/src/supabase_client.py` — new file
- `supabase/migrations/001_phase2_schema.sql` — new file (or equivalent in Supabase dashboard)
- `backend/.env.example` — document `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`

**Acceptance criteria:**
- Running the migration SQL creates `videos` and `agent_beliefs` tables with RLS enabled
- `get_supabase_client()` returns an authenticated client using `SUPABASE_SERVICE_KEY`
- A smoke test: insert one row into `videos`, read it back, confirm round-trip
- Service key is read from env, never appears in logs

**Out of scope:** `publications` and `performance_snapshots` tables (Phase 3). Auth for end-user access (Phase 3). Row-level policies scoped to specific users (Phase 3 — Phase 2 uses service role exclusively).

**Implementation notes:** Use `supabase-py` (`supabase` package). Schema from `architecture/02-architecture.md` Layer 7. RLS must be enabled on both tables on creation, not as an afterthought. Seed the `agent_beliefs` table with the 12 rows from `architecture/03-agent-pipeline.md` section "Initial seed beliefs".

---

### B-05 — Persist video row on generate

**Owner:** Joscha
**Priority:** P1
**Estimate:** 1h
**Depends on:** B-04, and `POST /api/generate` in `main.py`
**Files touched:**
- `backend/src/main.py` — add Supabase insert after successful Hera submission in `generate_video()`

**Acceptance criteria:**
- After a successful `POST /api/generate`, a row is inserted into the `videos` table with `hera_video_id`, `listing_url`, `outpaint_enabled`, `listing_data` (full JSON), `agent_decision` (full JSON), `hera_payload` (exact body sent)
- A Supabase insert failure does NOT cause the endpoint to 500 — log the error and continue (the user still gets their video)
- `video_url` and `hera_project_url` are populated from the Hera response if present, else `null`

**Out of scope:** Updating `video_url` after polling completes (Phase 3 cleanup job). Exposing the `videos` table to the frontend (Phase 3).

**Implementation notes:** Wrap the Supabase insert in a `try/except` that logs at ERROR but does not reraise. The insert runs after `r.json()` is confirmed successful to avoid persisting failed submissions.

---

### B-06 — Beliefs injection into classifier

**Owner:** Joscha
**Priority:** P1
**Estimate:** 1.5h
**Depends on:** B-04
**Files touched:**
- `backend/src/agent/beliefs.py` — new file
- `backend/src/agent/classifier.py` — inject beliefs into system prompt
- `backend/src/agent/orchestrator.py` — fetch beliefs, pass to classifier

**Acceptance criteria:**
- `fetch_beliefs(limit: int = 10) -> list[Belief]` queries `agent_beliefs` ordered by `confidence DESC LIMIT 10`
- Beliefs are injected into the classifier system prompt as described in `architecture/03-agent-pipeline.md` "Phase 2 adds a 'Your beliefs' block"
- `AgentDecision.beliefs_applied` is populated from the classifier's JSON output
- If `SUPABASE_URL` is not set, `fetch_beliefs()` returns an empty list and the classifier runs without beliefs (graceful degradation — Phase 1 behavior is preserved)
- Verified with a log line: `classifier: beliefs_injected=N beliefs_applied=M`

**Out of scope:** Updating belief confidence from performance data (Phase 3). Filtering out beliefs below 0.5 confidence (Phase 3 — for now, top 10 by confidence is sufficient).

**Implementation notes:** The `Belief` Pydantic model is defined in `backend/src/agent/models.py`. If the Supabase query fails (network error), treat it the same as "no Supabase configured" — return empty list, log at WARNING.

---

### B-07 — Playwright scraper (live listings)

**Owner:** Joscha
**Priority:** P2
**Estimate:** 4h
**Depends on:** none (parallel)
**Files touched:**
- `backend/src/agent/scraper.py` — new file
- `backend/src/main.py` — swap `load_fixture` for `scrape_listing` (behind a feature flag)
- `backend/requirements.txt` or `pyproject.toml` — add `playwright`

**Acceptance criteria:**
- `scrape_listing(url: str) -> ScrapedListing | None` launches a headless Chromium context, navigates to the URL, extracts `__NEXT_DATA__`, and maps to `ScrapedListing`
- If `__NEXT_DATA__` is missing or schema-shifted, falls back to LLM extraction from `page.textContent()`
- On any scrape failure (timeout, block, parse error) returns `None` — the caller raises `503 scrape_blocked`
- Verified against one live Airbnb URL in dev (not CI — CI uses fixtures only)
- The scraper is enabled only when `ENABLE_LIVE_SCRAPE=true` env var is set; otherwise fixture loader is used

**Out of scope:** Persistent browser profile management (session reuse, cookie storage). VRBO/Booking.com parsing. Proxy rotation.

**Implementation notes:** `playwright-python` (`playwright` pip package), not `playwright-cli`. Install browsers with `playwright install chromium`. Use a persistent context only if needed for bot avoidance — start with a plain context and escalate. The `__NEXT_DATA__` extraction is: `await page.eval_on_selector("script#__NEXT_DATA__", "el => JSON.parse(el.textContent)")`. Map the Airbnb JSON to `ScrapedListing` via a dedicated parser function. Keep the parser separate from the browser logic so it's testable without a browser.

**Risk: HIGH.** Airbnb actively blocks scrapers. There is a real chance this does not work reliably in 24h. Mitigation: keep the fixture fallback working; use the scraper only for the "impressive live demo moment" and pre-capture fixtures for the safe demo path.

---

## Frontend Tickets (Karl)

### F-01 — Wire outpaint toggle to API call

**Owner:** Karl
**Priority:** P0
**Estimate:** 1h
**Depends on:** Ticket 0
**Files touched:**
- `frontend/src/api/client.ts` — update `postListing` to accept and send `outpaint_enabled`
- `frontend/src/components/UrlInput.tsx` — confirm toggle state is passed through to `handleGenerate`
- `frontend/src/App.tsx` — pass `outpaint_enabled` from toggle state into `postListing`

**Acceptance criteria:**
- When the outpaint toggle is on, `POST /api/listing` body includes `outpaint_enabled: true`
- When the toggle is off (default), body includes `outpaint_enabled: false` or omits the field
- Toggle state is preserved while the user is on the `idle` screen; it resets to `false` on `goIdle()`
- Verified by checking the Network tab in DevTools: request body contains the correct flag

**Out of scope:** Any visual indication in the result that outpaint ran (that is F-04). Loading state changes during outpaint wait (that is F-03).

**Implementation notes:** `postListing` signature becomes `postListing(listing_url: string, outpaint_enabled: boolean): Promise<ListingResponse>`. The toggle already exists in `UrlInput.tsx` (per `01-ui-flow.md`) — confirm it exposes its state via a callback or ref. If the toggle is not yet in the component, add it now as a simple `<input type="checkbox">` with a label.

---

### F-02 — Wire regenerate button to `/api/regenerate`

**Owner:** Karl
**Priority:** P0
**Estimate:** 1h
**Depends on:** Ticket 0, B-02 (or mock it)
**Files touched:**
- `frontend/src/api/client.ts` — add `postRegenerate()` function
- `frontend/src/App.tsx` — replace `goIdle()` call in the Regenerate button with `handleRegenerate()`

**Acceptance criteria:**
- Clicking "Regenerate" on the `done` screen calls `POST /api/regenerate` with the current `listing_url`, `listing`, and `decision`
- On success, transitions to `generating` screen with the new `video_id`
- On failure, transitions to `error` screen with an appropriate message
- The reasoning card content does not change during regenerate (same decision, new render)
- While the regenerate call is in-flight, the button is disabled and shows "Regenerating..."

**Out of scope:** Producing a different angle on regenerate (Phase 3). Changing parameters (seed, style) on regenerate.

**Implementation notes:** `handleRegenerate()` can reuse the existing polling logic — after getting `video_id` from `/api/regenerate`, set state to `{ screen: "generating", ..., videoId: video_id }` and the existing `useEffect` polling loop picks it up. Mock B-02 with a hardcoded `video_id` string during development if Joscha's endpoint isn't ready yet.

---

### F-03 — Outpaint loading state indicator

**Owner:** Karl
**Priority:** P0
**Estimate:** 0.5h
**Depends on:** F-01
**Files touched:**
- `frontend/src/App.tsx` — conditionally show outpaint loading copy when `outpaint_enabled` is true

**Acceptance criteria:**
- When `outpaint_enabled=true` and the app is in the `generating` state, the status row for "Reading the listing..." shows "Outpainting photos to 9:16..." as an additional stage label
- The label is only shown when `outpaint_enabled` is true — no UI change when toggle is off
- No spinner or animation change is required — just copy swap

**Out of scope:** Per-photo progress (not exposed by the API). Timing estimate for outpaint duration.

**Implementation notes:** Pass `outpaint_enabled` into the generating screen's props or read it from `state`. The existing `StatusRow` components in the generating screen handle the stage labels — add one more conditional row. This is a 30-minute ticket because the stage label infrastructure already exists.

---

### F-04 — Beliefs applied display in RationaleRail

**Owner:** Karl
**Priority:** P1
**Estimate:** 1h
**Depends on:** Ticket 0
**Files touched:**
- `frontend/src/components/RationaleRail.tsx` — add "Beliefs applied" section
- `frontend/src/types.ts` — already updated in Ticket 0

**Acceptance criteria:**
- If `decision.beliefs_applied` is a non-empty array, a "Beliefs applied" section appears at the bottom of the RationaleRail
- Each belief `rule_key` is displayed as a short tag (e.g. `hook_with_hero_shot`)
- If `beliefs_applied` is empty or absent, the section is hidden — no empty state, no placeholder
- The tags follow the existing RationaleRail visual style (no new component library additions)

**Out of scope:** Expanding a belief tag to show its `rule_text` (Phase 3 transparency). Editing beliefs from the UI (Phase 3).

**Implementation notes:** The `rule_key` strings are already human-readable slugs (`hook_with_hero_shot`, `duration_15s`). Display them as-is, replacing underscores with spaces if desired. Use a simple `<div className="flex flex-wrap gap-1">` of `<span>` tags — no badge component needed.

---

### F-05 — Download button robustness

**Owner:** Karl
**Priority:** P1
**Estimate:** 0.5h
**Depends on:** none (already partially shipped)
**Files touched:**
- `frontend/src/App.tsx` — replace the existing `<a href download>` with a fetch-based download

**Acceptance criteria:**
- Clicking "Download MP4" triggers a browser download, not a new tab
- The filename defaults to `hera-video.mp4` (or listing title slug if available)
- If `file_url` is expired or unreachable, the button shows a brief "Link expired — regenerating..." state and calls `GET /api/videos/{video_id}` to refresh the URL (only if `video_id` is available in state)
- On URL refresh failure, shows "Download failed. Try regenerating."

**Out of scope:** Server-side download proxy. S3 pre-signed URL refresh endpoint (use the existing `GET /api/videos/{video_id}` which re-fetches from Hera).

**Implementation notes:** The existing `<a href={state.fileUrl} download>` already works for non-CORS URLs. Airbnb CDN URLs and Hera S3 URLs may have CORS headers that prevent `download` attribute from working in some browsers. A `fetch(url) + URL.createObjectURL(blob)` pattern handles this — but only add the complexity if the simple `<a download>` breaks in testing. Add `video_id` to the `done` state shape so the refresh logic can reference it.

**Note:** `AppState` `done` variant currently lacks `videoId`. Add it: `{ screen: "done"; listing: ScrapedListing; decision: AgentDecision; fileUrl: string; videoId: string }`. Update `setState` call in the polling loop accordingly.

---

### F-06 — Error messages for Phase 2 error codes

**Owner:** Karl
**Priority:** P1
**Estimate:** 0.5h
**Depends on:** none
**Files touched:**
- `frontend/src/components/ErrorState.tsx` — add new error code mappings

**Acceptance criteria:**
- `scrape_blocked` → "Airbnb blocked us on that listing. Try a different one, or paste a listing we've seen before."
- `scrape_failed` → "We couldn't read that listing. The page may have changed. Try again."
- All existing Phase 1 error codes continue to work
- Unrecognized error codes fall through to the raw message (existing behavior)

**Out of scope:** Retry-with-backoff (Phase 1 decision, still deferred). Suggesting alternative listings.

**Implementation notes:** The error code is in the backend response body as `detail.error`. The current `ErrorState` displays `message` as a string — check if it already parses the JSON body or just shows raw text. If it shows raw text, this ticket adds a simple map lookup.

---

## Merge-Conflict Hot Spots

| File | Owner | Protocol |
|---|---|---|
| `frontend/src/types.ts` | Karl | Joscha sends type additions as a comment on the PR or a shared gist. Joscha never edits this file directly. |
| `backend/src/agent/models.py` | Joscha | Karl reads the final model shapes from Joscha's branch via `git fetch` before F-01 and F-04. Karl never edits this file. |
| `backend/src/main.py` | Joscha | Karl does not touch this file. Any route-shape questions go to Joscha via Slack/message. |
| `backend/src/agent/orchestrator.py` | Joscha | Karl does not touch this file. |
| `frontend/src/App.tsx` | Karl | Joscha does not touch this file. |
| `frontend/src/api/client.ts` | Karl | Joscha does not touch this file. New endpoint shapes communicated via Ticket 0 contract. |

**The only dangerous moment:** Ticket 0 requires both to edit their respective contract files simultaneously. Strategy: Joscha pushes the Pydantic changes to his branch first. Karl pulls a copy of the model shapes (by reading the file or via a message) and writes the TS side. They never edit the same file.

---

## Suggested 24-Hour Timeline

Times are relative to hackathon start. Both work in parallel after Hour 1.

```
Hour 0–1    [BOTH]      Synchronous: finalize Ticket 0 contract. Joscha pushes Pydantic
                        changes. Karl mirrors in TS. Both confirm contract is locked.

Hour 1–2    [Joscha]    B-01: wire outpaint flag through listing endpoint.
            [Karl]      F-01: wire outpaint toggle to API call. F-02 started (mock backend).

Hour 2–4    [Joscha]    B-02: /api/regenerate endpoint (1h). B-03: Nanobanana outpainter (2h).
            [Karl]      F-02: complete regenerate (1h). F-03: outpaint loading state (0.5h).
                        F-06: Phase 2 error codes (0.5h).

Hour 4–5.5  [Joscha]    B-04: Supabase schema bootstrap.
            [Karl]      F-04: beliefs applied display in RationaleRail. F-05: download button.

            >>> INTEGRATION CHECKPOINT 1 (Hour 5.5) <<<
            Karl pulls Joscha's branch. Smoke test: outpaint toggle end-to-end.
            Joscha's /api/regenerate verified from Karl's UI.

Hour 5.5–7  [Joscha]    B-05: persist video row on generate.
            [Karl]      Polish: loading copy, error messages. Fix any integration bugs.

Hour 7–8.5  [Joscha]    B-06: beliefs injection into classifier.
            [Karl]      Test full flow with beliefs. Fix any display issues in RationaleRail.

            >>> INTEGRATION CHECKPOINT 2 (Hour 8.5) <<<
            Full Phase 2 P0+P1 stack running end-to-end on develop.
            Demo rehearsal run: paste URL, toggle outpaint on, generate, regenerate, download.

Hour 8.5–12 [Joscha]    B-07: Playwright scraper (P2, only if time). Otherwise: add more
                        fixtures, harden error paths, write a simple test for B-03.
            [Karl]      UI polish, responsive fixes, demo prep. Pre-render the demo video.

Hour 12–24  [BOTH]      Buffer. Demo polish. Pre-render backup videos. Sleep.
```

**Critical path:** Ticket 0 → B-01 → B-03 → Integration Checkpoint 1. Everything else can slip to P1 without killing the demo.

---

## Cut List (P2 / Deferred)

| Item | Priority | Why deferred |
|---|---|---|
| **B-07: Playwright live scraper** | P2 | Airbnb anti-bot is unpredictable in a 24h window. A failed scrape during the live demo is worse than a polished fixture. Ship fixtures, use scraper only if it works cleanly in testing. |
| **Supabase: `publications` and `performance_snapshots` tables** | P2 (Phase 3) | No social publishing in Phase 2. Schema exists in the architecture doc but building it now provides zero demo value. |
| **Belief confidence updates from performance data** | P2 (Phase 3) | Requires published videos with analytics data. Nothing to update from in 24h. |
| **`style_id` mapping from property category** | P2 | Architecture doc describes category-to-Hera-style mapping. Hera styles with the specified IDs (`beach-warm`, `urban-minimal`, etc.) need to be created in the Hera dashboard first — pre-hackathon setup that may not have happened. Skip unless the style IDs are confirmed to exist. |
| **Storyboard (`list[Scene]`) output from agent** | P2 | The Phase 2 storyboard structure in `03-agent-pipeline.md` is a significant agent rewrite. The current free-form `vibes/hook/pacing` model already produces good output. Do not rewrite the classifier schema mid-hackathon. |
| **SSE upgrade for status updates** | P2 (Phase 3) | Polling works. SSE adds reconnect logic and server-side fan-out complexity with no visible UX improvement over 5s polling. |
| **Per-scene timing in the transparency card** | P2 | Requires the storyboard output above. |
| **`GET /api/videos` (list user videos)** | P2 (Phase 3) | Requires auth. Not in Phase 2 scope. |
| **Rating/review data in scraper** | P2 | Architecture doc marks this as Phase 2 optional. Too noisy to parse reliably in a sprint; the agent works fine without it. |
| **Watermarking** | P2 (Phase 3) | No billing in Phase 2. |

### Minimum viable Phase 2 demo delta vs Phase 1

If everything above P1 is cut and even some P1 items slip, the demo still shows a clear upgrade over Phase 1 with these three things working:

1. **Outpaint toggle (B-01, B-03, F-01, F-03):** The audience sees portrait-format photos going into Hera, producing a better-composed 9:16 video. Toggle off vs. toggle on — visible difference on the same listing.
2. **Regenerate (B-02, F-02):** One click generates a new video from the same listing. Audiences understand this immediately.
3. **Beliefs applied display (B-06, F-04):** The reasoning card now shows which learned rules influenced the video. This is the transparency differentiator that generic AI video tools cannot show.

These three, working end-to-end, are a compelling demo. Everything else is gravy.
