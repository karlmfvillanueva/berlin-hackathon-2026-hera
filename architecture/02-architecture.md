# System Architecture — Airbnb Listing Video Agent

## Overview

The system is a thin, opinionated pipeline: **Frontend → FastAPI orchestrator → Agent → Hera → poll for video**.

Phase 1 (shipped MVP) runs entirely synchronous, in-process, stateless. Phase 2 layers in optional outpainting and a persistence + learning loop. Phase 3 is multi-platform and social posting.

This document is the single source of truth for what exists, what's planned, and where the seams are.

---

## Stack at a glance

| | Phase 1 (built) | Phase 2 (planned) | Phase 3 (later) |
|---|---|---|---|
| Frontend | Vite + React + TS | + outpaint toggle wired, regenerate, download | + dashboard, auth, OAuth flows |
| Backend | FastAPI on `:8000` | + Nanobanana client, Supabase client, performance cron | + multi-platform parsers, social-post adapters |
| Persistence | None (stateless) | Supabase Postgres | (unchanged) |
| Listing source | Pre-captured JSON fixtures | Live Playwright scrape | Airbnb + Booking + VRBO |
| Image processing | Pass through CDN URLs | Optional Nanobanana outpaint to 9:16 (toggle) | (unchanged) |
| Agent | Gemini 2.5 Pro via Vertex AI (ADC) | + beliefs from DB | (unchanged) |
| Video render | Hera REST | (unchanged) | (unchanged) |
| Status updates | HTTP polling 5s | (unchanged) | Optional SSE upgrade |
| Neighborhood POIs | — | Optional **Google Maps Platform** (Geocoding + Places + Place Photo) + **Hera `/files`**; see [`05-neighborhood-google-places.md`](./05-neighborhood-google-places.md) | (unchanged) |

The Hera key never reaches the browser. Frontend talks only to FastAPI. **Maps/Places API keys** are server-only as well (`GOOGLE_PLACES_API_KEY` / `GOOGLE_MAPS_API_KEY` in `.env`, never `VITE_*`).

---

## Repo layout

```
backend/
  src/
    main.py                  # FastAPI app, routes, Hera proxy
    logger.py
    agent/
      __init__.py
      models.py              # Pydantic: Photo, ScrapedListing, AgentDecision, ...
      angles.py              # 6-angle taxonomy + prompt templates
      classifier.py          # Gemini SDK call → angle + rationale
      image_scorer.py        # Deterministic scoring → top 5 reference URLs
      prompt_builder.py      # Fill template, return Hera prompt string
      orchestrator.py        # run(listing) → AgentDecision
      fixture_loader.py      # Phase 1: load from fixtures/
      fixtures/              # Hand-captured listing JSON
      neighborhood_context.py  # Optional: Google Places + Hera /files for nearby refs
      # (see also: icp_classifier, location_enrichment, final_assembly, orchestrator)
      # Phase 2 additions:
      # scraper.py           # Live Playwright scraper, replaces fixture loader as primary
      # outpainter.py        # Nanobanana client (toggle-gated)
      # beliefs.py           # SELECT top 10 beliefs by confidence DESC
      # performance/         # cron + analytics polling, kept off the request path
frontend/
  src/
    App.tsx
    components/
    api/client.ts
    types.ts
```

Phase 2 modules live alongside the existing ones, not in a parallel tree. Replace the fixture loader call in `orchestrator.run()` with a scraper call when Phase 2 lands. The agent itself does not change.

---

## API surface

The MVP exposes three application endpoints plus a Hera passthrough. Phase 2 and 3 add to this list rather than replace it.

### `POST /api/listing` — load and classify (Phase 1)

Returns instantly (Gemini call is the only blocking work, ~1–3s). The frontend uses this to paint the reasoning card before any rendering starts.

**Request:**
```json
{ "listing_url": "https://www.airbnb.com/rooms/12345678" }
```

**Response 200:**
```json
{
  "listing": { "...ScrapedListing..." },
  "decision": {
    "angle_id": "remote_work",
    "angle_label": "Remote Work Base",
    "confidence": 0.84,
    "rationale": "The title mentions a dedicated workspace…",
    "hera_prompt": "Create a 15-second vertical motion graphics video…",
    "selected_image_urls": ["https://…", "…"]
  }
}
```

**Errors:**
- `404 fixture_not_found` (Phase 1) — listing URL has no fixture. Replaced in Phase 2 by `scrape_blocked` / `scrape_failed`.
- `500 classifier_failed` — Gemini call returned non-JSON or the schema didn't validate.

### `POST /api/generate` — submit to Hera (Phase 1)

Takes the decision the frontend already has and submits to Hera.

**Request:**
```json
{ "decision": { "...AgentDecision..." } }
```

**Response 200:**
```json
{
  "video_id": "hera-abc123",
  "decision": { "...AgentDecision..." }
}
```

**Errors:**
- `502 hera_unreachable` — Hera API is down or timed out.
- `500 hera_submission_failed` — Hera returned 4xx/5xx.

### `GET /api/videos/{video_id}` — status passthrough (Phase 1)

Frontend polls every 5s. Backend proxies to `GET https://api.hera.video/v1/videos/{video_id}` and reshapes minimally.

**Response 200:**
```json
{
  "video_id": "hera-abc123",
  "project_url": "https://app.hera.video/motions/...",
  "status": "in-progress" | "success" | "failed",
  "outputs": [
    {
      "status": "success",
      "file_url": "https://hera-cdn.com/exports/video.mp4",
      "config": { "format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p" }
    }
  ]
}
```

No caching in Phase 1 — each poll hits Hera directly.

### `POST /api/videos` — direct passthrough (Phase 1)

Thin proxy to `POST https://api.hera.video/v1/videos` for raw access during demos and probes. Not used by the production frontend flow. Kept because it's already wired and cheap to maintain.

### `GET /api/health`

Smoke test: `{ ok: true, hera_key_loaded: bool }`. Never reveals the key.

### Neighborhood / Google Places (optional, Phase 2 render)

Not a separate HTTP route. During **`POST /api/generate`**, after photo analysis, the orchestrator may call **`neighborhood_context.fetch_neighborhood_context`**. If `GOOGLE_PLACES_API_KEY` (or `GOOGLE_MAPS_API_KEY`) and `HERA_API_KEY` succeed, the returned **`AgentDecision`** includes `neighborhood_places` and `neighborhood_reference_urls`, and the Hera create payload adds **`reference_image_urls`** for those venue stills. Spec: [`05-neighborhood-google-places.md`](./05-neighborhood-google-places.md).

### Phase 2 additions

- `POST /api/regenerate` — accept `{ video_id }` or `{ decision, seed }`, kick off a new Hera job, return new `video_id`.
- `GET /api/videos` (authed, Phase 3) — list user's prior videos. Reads from `videos` table.

---

## Phase 1 pipeline (shipped)

Synchronous, single request. No queue, no background jobs.

```
client                       FastAPI                          Hera
  │                             │                                │
  │ POST /api/listing           │                                │
  │ { listing_url }             │                                │
  ├────────────────────────────▶│                                │
  │                             │ load_fixture(url)              │
  │                             │ ScrapedListing                 │
  │                             │                                │
  │                             │ orchestrator.run(listing)      │
  │                             │   ├─ classifier (Gemini)       │
  │                             │   ├─ image_scorer              │
  │                             │   └─ prompt_builder            │
  │                             │ AgentDecision                  │
  │ 200 { listing, decision }   │                                │
  │◀────────────────────────────┤                                │
  │                             │                                │
  │ POST /api/generate          │                                │
  │ { decision }                │                                │
  ├────────────────────────────▶│                                │
  │                             │ POST /videos                   │
  │                             ├───────────────────────────────▶│
  │                             │ { video_id, project_url }      │
  │                             │◀───────────────────────────────┤
  │ 200 { video_id, decision }  │                                │
  │◀────────────────────────────┤                                │
  │                             │                                │
  │ GET /api/videos/{id}  (×N)  │                                │
  ├────────────────────────────▶│                                │
  │                             │ GET /videos/{id}               │
  │                             ├───────────────────────────────▶│
  │                             │◀───────────────────────────────┤
  │ 200 { status, outputs }     │                                │
  │◀────────────────────────────┤                                │
```

Total endpoints called per video: 3 backend, 2 Hera (1 create + N polls). No DB, no queue, no cron.

---

## Phase 2 pipeline (planned)

Same request shape, more layers behind `/api/listing`:

```
POST /api/listing { listing_url, outpaint_enabled }
  │
  ▼
[scraper.py]                                    # Phase 2 replaces fixture_loader
  Playwright headless → ScrapedListing
  │
  ▼
[image_scorer.py] → top 5 photo URLs
  │
  ▼
if outpaint_enabled:                            # Phase 2 toggle
  [outpainter.py] → 5× Nanobanana calls in parallel
  yields 5× 9:16 portrait URLs hosted on Nanobanana CDN
else:
  pass through original URLs
  │
  ▼
[classifier.py] → AgentDecision (with beliefs from DB)
  │
  ▼
return ListingResponse
```

`POST /api/generate` is unchanged. The video record gets persisted to Supabase here (see Layer 7).

---

## Layer 1: Frontend

Already specified in `01-ui-flow.md`. Repeating the parts that bind to this layer:

- Vite + React + TS, dev `:5173`.
- Reads `VITE_BACKEND_URL` from env. Never reads any Hera or Gemini key.
- Single screen, state machine. No router.
- HTTP polling for status. SSE is a Phase 3 optional upgrade — not started.

**Why not Next.js / SSR / SSE:** the MVP works on Vite + polling. SSR adds zero value when the only stateful page is a single client-side state machine. SSE adds real complexity (long-lived connections, reconnect logic, server-side fan-out) for a UX gain that's marginal over a 5-second poll. Defer until there's a reason.

---

## Layer 2: API orchestrator (FastAPI)

- FastAPI app in `backend/src/main.py`.
- Single `httpx.AsyncClient` configured with the Hera base URL and `x-api-key` header, lifecycle-managed via FastAPI's `lifespan`.
- All request/response bodies are Pydantic models. No untyped dicts crossing the boundary.
- Pipeline runs in-process; no Celery, no Redis, no queue.

**Why not Next.js API routes / Vercel serverless:**
- Playwright + Chromium is too large for Vercel's 50 MB function size limit. We will need Playwright in Phase 2 — designing around that constraint now would mean Browserless or a sidecar.
- FastAPI keeps the agent logic in Python, which the team already writes daily. Splitting Python (agent) and JS (orchestrator) doubles the deployment surface.
- The MVP runs on FastAPI today. There is no good reason to switch.

If we need horizontal scale post-Phase-2, the FastAPI service is trivially deployable to Fly.io / Render / Railway (single container, no exotic deps).

---

## Layer 3: Listing source

### Phase 1: Fixtures

`backend/src/agent/fixture_loader.py` reads JSON files from `backend/src/agent/fixtures/`, keyed by listing URL or ID. Listings are hand-captured via a DevTools snippet in the user's real browser session. This sidesteps Airbnb's anti-bot during the hackathon sprint.

### Phase 2: Live Playwright scrape

Replace the fixture loader with a Playwright-driven scraper using a persistent context (real browser profile) to dodge basic bot detection. Strategy:

1. Navigate to the listing URL.
2. Wait for the photo carousel to render.
3. Extract `__NEXT_DATA__` from the page source — Airbnb embeds the full listing as JSON for SSR hydration.
4. Map to the same `ScrapedListing` Pydantic model the fixture loader produces. **The agent layer does not know whether data came from a fixture or a live scrape.** This is the seam.

Fallback: if `__NEXT_DATA__` is missing or the schema has shifted, fall back to LLM extraction from `page.textContent()` against a structured prompt. Only used when the structured path fails.

Photos: Airbnb CDN URLs are public and don't require auth. Pass them straight to Hera (or to Nanobanana first, if outpaint is on).

**Risks:**
- Anti-bot escalation. Mitigation: hold one or two pre-captured fixtures as a fallback for live demos.
- HTML schema drift. Mitigation: monitor the LLM-extraction fallback rate and re-anchor the parser when it spikes.

---

## Layer 4: Image processing — Nanobanana outpainting (Phase 2, toggle-gated)

**Purpose:** Convert landscape (4:3 / 16:9) listing photos to 9:16 portrait without cropping, by extending vertically (AI-generated ceiling above, floor below). This preserves the full original image content.

**Why this exists as a layer rather than letting Hera handle aspect ratio:** Hera will accept landscape references and produce 9:16 output, but it crops or letterboxes. For listings where the visual subject (a pool, a view) is centered horizontally and uses the full landscape frame, vertical extension produces a more flattering portrait composition than a center crop. The user has confirmed they want this as a feature; the toggle on the landing page lets us A/B the perceived quality on a single listing.

**Pipeline per photo (5 in parallel):**

```
1. Detect current aspect ratio (httpx HEAD or download to a buffer).
2. Compute target dimensions: new_height = original_width × (16/9).
3. Compute extension: total_extension = new_height - original_height,
   split evenly top + bottom.
4. Call Nanobanana outpaint endpoint:
     direction: top + bottom
     target_aspect_ratio: 9:16
5. Return Nanobanana CDN URL of the outpainted image.
```

**Configuration:**
- `outpaint_enabled` flag flows in via `POST /api/listing` body. Default off until we have evidence the outpainted version performs better; then flip default and keep the toggle for the demo narrative.
- Per-photo timeout 30s. On any single-photo failure, fall back to that photo's original URL (Hera handles the mixed aspect refs gracefully).

**Why outpainting works for listings:** the extended areas are almost always ceiling (white/neutral) and floor (wood/tile/carpet) for interiors, or sky and ground for exteriors. These are visually repetitive and simple for the model to generate convincingly.

---

## Layer 5: Agent

Full specification in `03-agent-pipeline.md`. Summary for this document:

**Input:**
- `ScrapedListing` (from fixture loader or scraper).
- Phase 2: top 10 `agent_beliefs` rows ordered by confidence, fetched from Supabase. Phase 1 uses the same beliefs hardcoded into `angles.py`.

**Steps (single Gemini call with structured output):**
1. Score each photo against angle priority keywords using deterministic Python (`image_scorer.py`).
2. Send listing summary + photo labels to Gemini 2.5 Pro on Vertex AI (ADC). Receive `{ angle_id, confidence, rationale }` as JSON.
3. Fill the angle's prompt template with listing fields (`prompt_builder.py`).
4. Return `AgentDecision` with the angle, rationale, top 5 image URLs (post-outpaint if enabled), and the assembled Hera prompt.

**Why the angle taxonomy stayed intent-based (`urban_escape`, `beach_retreat`, `remote_work`, `entertainer`, `romantic_getaway`, `family_base`):** the MVP shipped with this taxonomy and prompts are tuned to it. Property-type categories (beach / mountain / urban / luxury / unique) are demoted to a *style-mapping helper* — see `03-agent-pipeline.md` for how categories get used to pick a Hera `style_id` and palette without overriding the angle-driven editorial decision.

---

## Layer 6: Video rendering — Hera REST

Direct REST against `https://api.hera.video/v1`, no MCP. Auth via `x-api-key` header.

**Calls used:**

| Endpoint | When | Why |
|---|---|---|
| `POST /videos` | After agent produces decision | Submit job, get `video_id` |
| `GET /videos/{id}` | Polling loop, every 5s | Wait for `status === "success"` |
| `POST /files` | (not used in Phase 1, optional Phase 2) | Re-upload images if Airbnb CDN URLs are ever rejected as references |

**Submitted parameters:**

| Parameter | Value | Source |
|---|---|---|
| `prompt` | Agent-built natural language scene plan | `AgentDecision.hera_prompt` |
| `reference_image_urls` | Top 5 photos (post-outpaint if enabled), ordered by scene usage | `AgentDecision.selected_image_urls` |
| `duration_seconds` | 15 | Hardcoded in `main.py`. Agent may override later. |
| `outputs[0]` | `mp4`, `9:16`, `30fps`, `1080p` | Hardcoded in `main.py` |
| `style_id` | (Phase 2) From the property-category-to-style table | See `03-agent-pipeline.md` |

**Latency, observed:** 147s wall time for a 15s 9:16 1080p video (probe). Submission is sub-second; rendering is the bottleneck. Demo strategy is to pre-render the demo video and let the reasoning card carry the live audience while the pre-rendered MP4 plays.

---

## Layer 7: Persistence + performance learning (Phase 2)

**Out of scope for Phase 1.** The MVP is stateless — every request runs the full pipeline against fixtures and Hera, nothing persists. The schema below is what we add in Phase 2.

### Supabase Postgres schema

```sql
-- One row per video the agent ever generated
create table videos (
  id uuid primary key default gen_random_uuid(),
  listing_url text not null,
  hera_video_id text not null,
  hera_project_url text,
  video_url text,                       -- final MP4, refreshed on demand (S3 pre-signed, 24h)
  outpaint_enabled boolean not null default false,
  listing_data jsonb not null,          -- full ScrapedListing
  agent_decision jsonb not null,        -- full AgentDecision
  hera_payload jsonb not null,          -- exact body sent to POST /videos
  created_at timestamptz default now()
);

-- Phase 3: one row per platform publication
create table publications (
  id uuid primary key default gen_random_uuid(),
  video_id uuid references videos(id) on delete cascade,
  platform text not null,               -- "instagram" | "tiktok" | "youtube"
  platform_post_id text,
  published_at timestamptz default now()
);

-- Phase 3: periodic analytics pulls per publication
create table performance_snapshots (
  id uuid primary key default gen_random_uuid(),
  publication_id uuid references publications(id) on delete cascade,
  snapshot_at timestamptz default now(),
  views int, likes int, saves int, shares int, comments int,
  watch_through_rate float,
  avg_watch_seconds float
);

-- Agent's editorial rules. Hardcoded seed in Phase 2. Self-updating from Phase 3.
create table agent_beliefs (
  id uuid primary key default gen_random_uuid(),
  rule_key text unique not null,        -- e.g. "pool_hook_priority"
  rule_text text not null,              -- human-readable rule the agent applies
  confidence float default 0.5,
  evidence_count int default 0,
  last_updated timestamptz default now()
);
```

RLS is enabled on every table from day 0 (per global security rule). Phase 2 has no end-user auth, so writes go through a service-role key on the backend; reads are server-side only.

### Belief update cycle (Phase 3, when publications start happening)

```
Every 6 hours (cron):
  1. For each publication with a connected social account:
     - Pull latest analytics via the platform API
     - Insert a performance_snapshot row

  2. For each video with >24h of post-publication data:
     - Look up its agent_decision JSONB
     - Compare its performance against the population average

  3. Update beliefs:
     - Pool-hook beach videos outperforming the average by >20%
       → confidence += 0.05, evidence_count += 1 on rule_key='pool_hook_priority'
     - 15s-duration videos outperforming 30s on the same property type
       → same pattern on rule_key='optimal_duration_15s'
```

Initial seed beliefs (loaded into `agent_beliefs` on Phase 2 first deploy) are listed in `03-agent-pipeline.md`.

### How beliefs flow back into the agent

Phase 2: `classifier.py` does a `SELECT rule_text FROM agent_beliefs ORDER BY confidence DESC LIMIT 10` and injects the results into the system prompt. The agent reads them, applies relevant ones, and writes the applied `rule_key`s into `AgentDecision.beliefs_applied` (new field, additive — does not break Phase 1 callers).

---

## Data flow summary

```
[Phase 1, shipped]

User pastes URL
   │
   ▼
[Vite frontend]
   │ POST /api/listing
   ▼
[FastAPI]
   ├─ fixture_loader → ScrapedListing
   ├─ image_scorer (deterministic) → top 5 URLs
   ├─ classifier (google-genai SDK) → angle + rationale
   └─ prompt_builder → AgentDecision
   │
   ▼
[Frontend renders reasoning card]
   │
   │ POST /api/generate
   ▼
[FastAPI]
   └─ POST /videos (Hera) → video_id
   │
   ▼
[Frontend polls GET /api/videos/{id} every 5s]
   │
   ▼
[Hera returns file_url on success → frontend plays video]


[Phase 2, additive]

User pastes URL with outpaint toggle on
   │
   ▼
[FastAPI POST /api/listing]
   ├─ scraper (Playwright) → ScrapedListing                      [replaces fixtures]
   ├─ image_scorer → top 5 URLs
   ├─ outpainter (Nanobanana) → 5× 9:16 portrait URLs            [if toggle on]
   ├─ beliefs (Supabase) → top 10 by confidence                  [new]
   ├─ classifier → AgentDecision (beliefs in prompt)
   └─ prompt_builder
   │
   ▼
[Persist video row in Supabase]
   │
   ▼
[same /generate + polling flow as Phase 1]
```

---

## Infrastructure and deployment

### Phase 1 (running today)

Local dev only. `make dev` starts both servers. No production deployment yet.

### Phase 2 deployment options (when we ship)

| Component | Recommended | Why |
|---|---|---|
| FastAPI backend | Fly.io single container | Persistent context for Playwright, no 50 MB cold-start cap, no Lambda timeout |
| Vite frontend | Vercel static | Free tier covers it, fast CDN, no SSR requirement |
| Database | Supabase | RLS + Postgres + cron scheduler in one |
| Secrets | Fly.io secrets + Vercel env vars | Standard, no SaaS lock-in |

### Environment variables

```
# Backend
HERA_API_KEY=hera_…
GCP_PROJECT=…                        # Vertex AI for classifier + outpainter
GCP_LOCATION=us-central1             # ADC, no API key. `gcloud auth application-default login`
SUPABASE_URL=https://….supabase.co   # Phase 2 — also hosts outpainted-photos bucket
SUPABASE_SERVICE_KEY=eyJ…            # Phase 2 (server-only, service role)

# Frontend
VITE_BACKEND_URL=http://localhost:8000   # dev
VITE_BACKEND_URL=https://api.<domain>    # prod
```

The frontend bundle must never reference any of the backend secrets. The `VITE_` prefix is the only way values reach the bundle — keep secrets out of variables with that prefix.

---

## Error handling and resilience

| Failure point | Phase 1 handling | Phase 2 handling |
|---|---|---|
| Fixture missing | `404 fixture_not_found` | (replaced by scrape errors) |
| Scrape fails / blocked | n/a | `503 scrape_blocked` / `503 scrape_failed`, fall back to fixture if available |
| Photo fetch fails (outpaint path) | n/a | Skip that photo, continue with the rest. Min 2 photos required. |
| Nanobanana timeout | n/a | Use the original landscape URL for that photo. Hera handles mixed aspects. |
| Classifier returns invalid JSON | `500 classifier_failed` | Retry once with temperature 0; on second failure, hardcoded fallback decision (see `03-agent-pipeline.md`) |
| Hera POST /videos fails | `500 hera_submission_failed`, frontend shows retry button | Retry once server-side; same surface to client |
| Polling > 3 min | Frontend timeout, error state | Persist a `videos` row with status="failed" so we have a record |

Retry-with-backoff is explicitly **out of scope** until Phase 2 ships and we have the persistence layer to record retry state. Don't build it speculatively.

---

## Cost estimation per video

| Layer | Phase 1 | Phase 2 |
|---|---|---|
| Gemini (classifier) | 1 call, ~1.5K tokens | ~$0.005 |
| Gemini (Phase 2 photo ranking, optional) | — | ~$0.02 |
| Nanobanana outpaint (toggle on) | — | ~$0.10–0.25 for 5 photos |
| Hera `POST /videos` upload | — | — |
| Hera render | Credit-based | Credit-based |
| Supabase row + storage | — | rounding error |
| **Total per video (toggle off)** | **~$0.005 + Hera credits** | **~$0.025 + Hera credits** |
| **Total per video (toggle on)** | n/a | **~$0.13–0.28 + Hera credits** |

The outpaint toggle has a real cost asymmetry. That's another argument for keeping it user-controlled rather than always-on.
