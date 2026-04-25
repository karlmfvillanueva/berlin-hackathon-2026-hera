# System Architecture — StayMotion

## Architecture overview

StayMotion is a pipeline-oriented system with six layers: Frontend → API Orchestrator → Data Extraction → Image Processing → Creative Agent → Video Rendering. A seventh layer (Performance Learning) operates asynchronously and feeds back into the Creative Agent.

All inter-service communication is synchronous within a single API request lifecycle, except for Hera video rendering (async polling) and performance analytics (background cron).

---

## Layer 1: Frontend

**Stack:** Next.js 14+ (App Router), React, Tailwind CSS, deployed on Vercel.

**Responsibilities:**
- URL input and validation
- Real-time progress display via Server-Sent Events (SSE) or WebSocket from the orchestrator
- Video preview player (HTML5 `<video>` tag, MP4 source)
- Download handling
- OAuth flows for social media connections (stretch goal)

**Key routes:**
| Route | Component | Data source |
|---|---|---|
| `/` | `LandingPage` | Static |
| `/generate/[jobId]` | `GenerateProgress` | SSE stream from `/api/generate/[jobId]/stream` |
| `/video/[videoId]` | `VideoPreview` | GET `/api/video/[videoId]` |
| `/dashboard` | `Dashboard` | GET `/api/videos` |

**Frontend talks to:** Only the API orchestrator (Layer 2). Never directly to Hera, Nanobanana, or external services.

---

## Layer 2: API orchestrator

**Stack:** Next.js API routes (for hackathon simplicity — same deployment as frontend) OR FastAPI (if the team prefers Python for scraping/agent logic).

**Recommended for hackathon:** Next.js API routes with a background job processor. Use Vercel's serverless functions with a maximum execution time of 60s per function. Chain multiple function invocations for the full pipeline.

**Alternative for production:** FastAPI + Celery/Redis for job queue.

**Core endpoint:**

```
POST /api/generate
Body: { "url": "https://airbnb.com/rooms/12345" }
Response: { "jobId": "job_abc123" }
```

This endpoint kicks off the pipeline:
1. Validate URL
2. Create job record in database (status: `scraping`)
3. Start pipeline execution (see Pipeline Orchestration below)
4. Return jobId immediately

**Status streaming endpoint:**

```
GET /api/generate/[jobId]/stream
Response: Server-Sent Events stream
  data: { "step": "scraping", "message": "Analyzing your listing..." }
  data: { "step": "scraping_done", "stats": { "photos": 12, "rating": 4.8 } }
  data: { "step": "outpainting", "message": "Optimizing photos for mobile..." }
  data: { "step": "agent", "message": "Crafting your story...", "category": "beach" }
  data: { "step": "rendering", "message": "Rendering video..." }
  data: { "step": "done", "videoId": "vid_xyz789", "videoUrl": "https://..." }
```

**Pipeline orchestration pseudocode:**

```
async function runPipeline(jobId, listingUrl) {
  // Step 1: Scrape
  emit(jobId, "scraping")
  const listingData = await scrapeListing(listingUrl)
  emit(jobId, "scraping_done", { stats: listingData.stats })

  // Step 2: Rank photos and outpaint
  emit(jobId, "outpainting")
  const rankedPhotos = await rankPhotos(listingData.photos)  // LLM vision call
  const portraitPhotos = await Promise.all(
    rankedPhotos.slice(0, 5).map(photo => outpaintToPortrait(photo))
  )

  // Step 3: Upload assets to Hera
  emit(jobId, "uploading")
  const heraUrls = await Promise.all(
    portraitPhotos.map(photo => heraUploadFile(photo.url))
  )

  // Step 4: Run creative agent
  emit(jobId, "agent")
  const beliefs = await getTopBeliefs(10)  // from performance DB
  const heraPayload = await runCreativeAgent(listingData, heraUrls, beliefs)
  emit(jobId, "agent_done", { category: heraPayload.metadata.category })

  // Step 5: Render via Hera
  emit(jobId, "rendering")
  const { video_id } = await heraCreateVideo(heraPayload)

  // Step 6: Poll until done
  let status = "in-progress"
  while (status === "in-progress") {
    await sleep(3000)
    const result = await heraGetVideo(video_id)
    status = result.status
    if (status === "success") {
      emit(jobId, "done", { videoId: video_id, videoUrl: result.outputs[0].file_url })
    } else if (status === "failed") {
      emit(jobId, "error", { message: "Rendering failed" })
    }
  }
}
```

---

## Layer 3: Data extraction (Scraper)

**Stack:** Playwright (headless Chromium) running in a serverless function or container.

**Input:** Listing URL (e.g., `https://airbnb.com/rooms/12345`)

**Output:** Structured listing data object:

```typescript
interface ListingData {
  platform: "airbnb" | "booking" | "vrbo"
  title: string
  description: string
  location: {
    city: string
    country: string
    coordinates: { lat: number, lng: number }
  }
  photos: Array<{
    url: string
    caption?: string    // Airbnb provides captions for some photos
    category?: string   // "bedroom", "bathroom", "exterior", etc.
  }>
  amenities: string[]   // ["Pool", "Wi-Fi", "Kitchen", "Ocean view", ...]
  rating: number         // 4.85
  reviewCount: number
  topReviews: Array<{
    text: string
    rating: number
    author: string
  }>
  price: {
    amount: number
    currency: string
    period: string       // "night"
  }
  propertyType: string   // "Entire home", "Private room", etc.
  hostName: string
  guestCapacity: number
  bedrooms: number
  bathrooms: number
}
```

**Scraping strategy for Airbnb (MVP):**

Airbnb uses SSR with hydration data embedded in `<script>` tags. The most reliable extraction method:

1. Navigate to the listing URL with Playwright
2. Wait for the page to fully render (wait for photo carousel to load)
3. Extract the `__NEXT_DATA__` JSON from the page source (contains all listing data in structured form)
4. Parse the JSON and map to our `ListingData` interface
5. Download all photo URLs from the parsed data

**Fallback:** If `__NEXT_DATA__` is not available or the structure has changed, use LLM extraction:
1. Get the full page text via `page.textContent()`
2. Send to Claude with a structured extraction prompt
3. Parse the structured output

**Photo download:** Download all photos to temporary storage (or pass URLs directly if they're publicly accessible). Airbnb photo URLs are typically CDN URLs that don't require auth.

---

## Layer 4: Image processing (Nanobanana outpainting)

**Stack:** Nanobanana API for outpainting.

**Purpose:** Convert landscape/4:3 listing photos to 9:16 portrait format by extending the image vertically (adding ceiling above and floor below). This preserves the full original image content — nothing is cropped.

**Input:** Original listing photo URL (typically 4:3 or 16:9 landscape)

**Output:** 9:16 portrait version of the same photo with AI-generated ceiling/floor extensions

**Processing pipeline per photo:**

```
1. Download original photo
2. Detect current aspect ratio
3. Calculate required vertical extension:
   - Original: 4:3 (e.g., 2000×1500)
   - Target: 9:16
   - New height: original_width × (16/9) = 2000 × 1.778 = 3556px
   - Extension needed: 3556 - 1500 = 2056px (1028px top + 1028px bottom)
4. Call Nanobanana outpainting API:
   - Source image
   - Direction: top + bottom
   - Target aspect ratio: 9:16
5. Return outpainted image URL
```

**Why outpainting works well here:** The extended areas are almost always ceiling (white/neutral) and floor (wood/tile/carpet) for interiors, or sky and ground for exteriors. These are visually repetitive and simple for outpainting models to generate convincingly.

**Photo ranking (before outpainting):**

Not all listing photos should be included in the video. Use Claude's vision capability to rank photos:

```
System: You are a social media content expert. Rank these listing photos
by their visual impact for a 15-second property showcase video.
Prioritize: hero shots (pool, view, exterior), then unique amenities,
then interior highlights. Deprioritize: generic rooms, bathroom close-ups,
neighborhood shots.
Output: JSON array of photo indices ranked by priority.
```

Select top 5 photos for outpainting and video inclusion.

---

## Layer 5: Creative agent

**Stack:** Claude API (claude-sonnet-4-20250514 for speed, or claude-opus-4-20250414 for quality).

**Detailed specification in separate document:** `03-agent-pipeline.md`

**Summary:** The creative agent takes scraped listing data + outpainted portrait photos + performance beliefs, and outputs a complete Hera `create_video` API payload. It makes all editorial decisions: hook selection, story arc, scene ordering, timing, text overlays, style, and CTA.

**Input:**
- `ListingData` object from scraper
- Array of 5 outpainted portrait photo URLs (uploaded to Hera CDN)
- Top 10 agent beliefs from performance database

**Output:** Complete Hera `create_video` request body (see agent pipeline doc for full spec)

---

## Layer 6: Video rendering (Hera API)

**Stack:** Hera REST API (`https://api.hera.video/v1`)

**Authentication:** `x-api-key` header with team's hackathon API key.

**Three API calls in sequence:**

### 6a. Upload assets — `upload_file`

Upload each outpainted portrait photo to Hera's CDN so they can be referenced in the video generation prompt.

```
For each photo:
  POST upload_file
  Input: { url: "<photo_url>", file_name: "property_photo_1.jpg" }
  Output: { url: "https://hera-cdn.com/uploads/abc123.jpg" }
```

This returns hosted URLs that can be passed to `create_video` as `reference_image_urls` or in the `assets` array.

### 6b. Create video — `create_video`

Submit the creative agent's output as a video generation job.

```
POST /videos
Body: {
  "prompt": "<agent-generated prompt>",
  "reference_image_urls": ["<hera-cdn-url-1>", ..., "<hera-cdn-url-5>"],
  "duration_seconds": 15,
  "style_id": "<agent-selected-style>",
  "assets": [
    { "type": "image", "url": "<hera-cdn-url>" },
    ...
  ],
  "outputs": [
    {
      "format": "mp4",
      "aspect_ratio": "9:16",
      "fps": "30",
      "resolution": "1080p"
    }
  ]
}
Response: { "video_id": "vid_abc123", "project_url": "https://app.hera.video/motions/..." }
```

### 6c. Poll status — `GET /videos/{video_id}`

Poll every 3 seconds until status is `success` or `failed`.

```
GET /videos/vid_abc123
Response: {
  "video_id": "vid_abc123",
  "status": "success",
  "project_url": "https://app.hera.video/motions/...",
  "outputs": [
    {
      "status": "success",
      "file_url": "https://hera-cdn.com/exports/video.mp4",
      "config": { "format": "mp4", "aspect_ratio": "9:16", ... }
    }
  ]
}
```

**Important Hera parameters for our use case:**

| Parameter | Our usage | Rationale |
|---|---|---|
| `prompt` | Agent-generated, ~100–300 words | Describes the full video: scenes, transitions, text overlays, mood, pacing |
| `reference_image_urls` | Top 5 outpainted photos | Hera uses these as visual source material for the motion graphics |
| `duration_seconds` | 15 (default, agent can override) | Optimal for Reels/TikTok engagement |
| `style_id` | Agent-selected per property category | Ensures visual consistency. Create styles in Hera dashboard pre-hackathon |
| `outputs.aspect_ratio` | Always `"9:16"` | Vertical video for social |
| `outputs.resolution` | `"1080p"` | Standard for social platforms |

**Pre-hackathon setup needed:**
- Create 3–5 Hera styles (beach-warm, urban-minimal, mountain-cozy, luxury-dark, rural-bright) in the Hera dashboard
- Note down their `style_id` values for the agent to reference
- Test each style with a sample prompt to verify quality

---

## Layer 7: Performance learning pipeline (async)

**Stack:** Supabase (Postgres) for storage, cron job (Vercel Cron or standalone) for polling.

**This layer operates independently of the main generation pipeline.** It runs periodically, collects social media performance data, and updates the agent's belief system.

### Database schema

```sql
-- Videos table: tracks every generated video
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT NOT NULL,
  listing_url TEXT NOT NULL,
  hera_video_id TEXT NOT NULL,
  hera_project_url TEXT,
  video_url TEXT,                    -- final MP4 download URL
  listing_data JSONB NOT NULL,       -- full scraped listing data
  agent_decisions JSONB NOT NULL,    -- what the agent decided and why
  hera_payload JSONB NOT NULL,       -- exact payload sent to Hera
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Publications table: tracks where videos were posted
CREATE TABLE publications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id),
  platform TEXT NOT NULL,            -- "instagram", "tiktok", "youtube"
  platform_post_id TEXT,             -- platform's ID for the post
  published_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance snapshots: periodic analytics pulls
CREATE TABLE performance_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  publication_id UUID REFERENCES publications(id),
  snapshot_at TIMESTAMPTZ DEFAULT NOW(),
  views INTEGER,
  likes INTEGER,
  saves INTEGER,
  shares INTEGER,
  comments INTEGER,
  watch_through_rate FLOAT,          -- 0.0 to 1.0
  avg_watch_seconds FLOAT
);

-- Agent beliefs: the agent's learned editorial rules
CREATE TABLE agent_beliefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_key TEXT UNIQUE NOT NULL,     -- e.g., "pool_hook_performance"
  rule_text TEXT NOT NULL,           -- human-readable belief
  confidence FLOAT DEFAULT 0.5,     -- 0.0 to 1.0
  evidence_count INTEGER DEFAULT 0,
  last_updated TIMESTAMPTZ DEFAULT NOW()
);
```

### Belief update cycle

```
Every 6 hours (cron):
  1. For each publication with a connected social account:
     - Pull latest analytics via platform API (IG Insights, TikTok Analytics)
     - Insert performance_snapshot row

  2. For each video with >24h of performance data:
     - Look up agent_decisions (which hook, which style, which pacing, etc.)
     - Compare performance metrics against the population average

  3. Update beliefs:
     - If videos with pool hooks have higher watch-through-rate:
       UPDATE agent_beliefs SET confidence = confidence + 0.05,
       evidence_count = evidence_count + 1
       WHERE rule_key = 'pool_hook_priority'
     - If 15s videos outperform 30s:
       Same pattern for 'optimal_duration_15s'
```

### Initial hardcoded beliefs (for hackathon demo)

```json
[
  { "rule_key": "hook_with_hero_shot", "rule_text": "Always open with the single most visually striking photo (pool, view, exterior)", "confidence": 0.85 },
  { "rule_key": "duration_15s", "rule_text": "15 seconds is optimal for Reels and TikTok engagement", "confidence": 0.80 },
  { "rule_key": "cta_at_end", "rule_text": "End every video with a clear CTA showing booking link or QR code", "confidence": 0.90 },
  { "rule_key": "location_in_first_frame", "rule_text": "Show city name or neighborhood in the first 2 seconds", "confidence": 0.70 },
  { "rule_key": "social_proof_before_cta", "rule_text": "Place a review quote or rating badge just before the CTA", "confidence": 0.75 },
  { "rule_key": "warm_palette_for_beach", "rule_text": "Beach and tropical properties should use warm color palettes (amber, coral, golden tones)", "confidence": 0.80 },
  { "rule_key": "minimal_palette_for_urban", "rule_text": "Urban and city properties should use clean, minimal palettes (white, gray, single accent)", "confidence": 0.75 },
  { "rule_key": "fast_cuts_for_amenities", "rule_text": "Amenity showcase sequences should use quick cuts (0.8–1.2s per scene)", "confidence": 0.70 },
  { "rule_key": "slow_reveal_for_hero", "rule_text": "Hero shots deserve longer screen time (2–3s) with subtle zoom or pan", "confidence": 0.80 },
  { "rule_key": "music_over_voiceover", "rule_text": "Background music with text overlays outperforms voiceover for property videos", "confidence": 0.65 }
]
```

---

## Data flow summary

```
User pastes URL
  │
  ▼
[Frontend] ──POST──▶ [API Orchestrator]
                           │
                     ┌─────┴─────┐
                     ▼           ▼
              [Scraper]    [Photo Ranker]
              (Playwright)  (Claude Vision)
                     │           │
                     │     ┌─────┘
                     │     ▼
                     │  [Nanobanana Outpainting]
                     │  (4:3 → 9:16 per photo)
                     │     │
                     │     ▼
                     │  [Hera upload_file]
                     │  (get CDN URLs)
                     │     │
                     └──┬──┘
                        ▼
                 [Creative Agent]
                 (Claude API)
                 + beliefs from DB
                        │
                        ▼
                 [Hera create_video]
                        │
                   (poll get_video)
                        │
                        ▼
                 [Video URL returned]
                        │
                        ▼
                 [Frontend displays video]
```

---

## Infrastructure and deployment

### Hackathon deployment (simple)

| Component | Service | Notes |
|---|---|---|
| Frontend + API | Vercel (Next.js) | Single deployment, free tier sufficient |
| Database | Supabase | Free tier: 500MB, enough for hackathon |
| Scraper runtime | Vercel serverless OR separate container | Playwright needs headless Chromium |
| Secrets | Vercel env vars | `HERA_API_KEY`, `CLAUDE_API_KEY`, `NANOBANANA_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` |

### Playwright on Vercel caveat

Playwright + Chromium is too large for Vercel's serverless function size limit (50MB). Options:
1. **Browserless.io** — Managed headless browser as a service. Connect Playwright to their remote browser. Simplest for hackathon.
2. **Separate scraper service** — Run the scraper on Railway/Render as a separate API. The orchestrator calls it via HTTP.
3. **Use Airbnb's structured data directly** — Extract `__NEXT_DATA__` via a lightweight `fetch()` call without Playwright. May work for Airbnb specifically since they SSR everything.

**Recommendation for hackathon:** Option 3 first (try plain fetch), fall back to option 1 (Browserless) if needed.

### Environment variables

```
HERA_API_KEY=hera_...
CLAUDE_API_KEY=sk-ant-...
NANOBANANA_API_KEY=nb_...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
```

---

## Error handling and resilience

| Failure point | Handling |
|---|---|
| Scraper can't parse listing | Return clear error to user. Suggest checking URL. |
| Photo download fails | Skip that photo, continue with remaining. Min 2 photos required. |
| Nanobanana API timeout | Use original landscape photo as fallback (Hera can handle mixed aspect ratios) |
| Claude agent returns invalid JSON | Retry once with stricter prompt. If still fails, use hardcoded defaults. |
| Hera create_video fails | Retry once. If fails again, show error with "try again" button. |
| Hera polling timeout (>3 min) | Store job, notify user async (email/push). |

---

## Cost estimation per video generation

| Service | Call | Estimated cost |
|---|---|---|
| Claude (scraper assist) | 1 call, ~2K tokens | ~$0.01 |
| Claude (photo ranking) | 1 call with images, ~1K tokens | ~$0.02 |
| Nanobanana outpainting | 5 images | ~$0.10–0.25 |
| Claude (creative agent) | 1 call, ~3K tokens | ~$0.02 |
| Hera upload_file | 5 calls | Free (included) |
| Hera create_video | 1 video, 15s, 1080p | Depends on plan/credits |
| **Total per video** | | **~$0.15–0.30 + Hera credits** |
