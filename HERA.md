# HERA.md

Local reference for the Hera platform. Treat this as documentation an agent working in this repo should already know. Sourced from `docs.hera.video/llms-full.txt`, the OpenAPI spec at `docs.hera.video/api-reference/openapi.json`, the MCP page, and `hera.video` (April 2026).

For the absolute latest, the upstream sources are:
- https://docs.hera.video/api-reference/introduction
- https://docs.hera.video/mcp-server
- https://docs.hera.video/api-reference/openapi.json
- https://docs.hera.video/llms.txt and https://docs.hera.video/llms-full.txt

---

## 1. What Hera is

Hera is an **AI motion graphics generator**, not a general-purpose AI video tool. The output is animated design — animated text, charts, maps, on-brand graphics, transitions, scenes assembled like an After Effects template — rather than photoreal video.

Implications for an agent built on top of Hera:

- The medium is **graphics over time**, so the agent's editorial choices are about hooks, scene structure, on-screen copy, pacing, emphasis, and which numbers/charts to surface — not camera angles or lens choice.
- Hera's product page emphasizes "hundreds of templates", remixable, with chart and map primitives. Default canvas is 16:9 widescreen at 15s. (`hera.video`)
- The platform supports `style_id` (visual style preset) and `parent_video_id` (start from an existing video or template). These are the levers an opinionated agent should reach for first when "having taste."
- The platform is **asynchronous**: jobs queue, then resolve to one or more rendered output files. Plan UX accordingly (don't block; poll or stream status).

---

## 2. REST API at a glance

| | |
|--|--|
| Base URL | `https://api.hera.video/v1` |
| Auth header | `x-api-key: <HERA_API_KEY>` |
| Auth scheme name | `ApiKeyAuth` (per OpenAPI) |
| Content type (videos) | `application/json` |
| Content type (file upload) | `multipart/form-data` |
| Endpoints | `POST /videos`, `GET /videos/{video_id}`, `POST /files` |
| OpenAPI spec | https://docs.hera.video/api-reference/openapi.json |
| Doc revision (this file) | OpenAPI v1.0.0 / fetched 2026-04-25 |

Auth rule: API key is server-only. Never bundle in a frontend, never log it, never echo any portion of it. Everything client-facing must go through the backend proxy in this repo.

---

## 3. `POST /videos` — create a generation job

Creates an asynchronous motion graphics generation job and returns a `video_id` you can poll. The response returns immediately; rendering happens in the background.

### Request body — `CreateVideoInput`

| Field | Type | Required | Notes |
|---|---|---|---|
| `prompt` | string | yes | Describes subject, style, motion, colors. Be specific. |
| `outputs` | array of `ExternalExportConfig` | yes | 1–10 entries. Each defines one rendered file. |
| `duration_seconds` | number (1–60) | no | If omitted, defaults are used (or inherited from `parent_video_id`). |
| `style_id` | string | no | Visual style preset ID. |
| `brand_kit_id` | string | no | **Deprecated.** Use `style_id`. |
| `parent_video_id` | string | no | Start from an existing video or template ID — useful for iteration / variations. |
| `reference_image_url` | string | no | Single reference image. Use `reference_image_urls` instead if you have multiple. |
| `reference_image_urls` | string[] (max 5) | no | Multi-image style/content reference. |
| `reference_video_url` | string | no | Reference video for style/structure cues. |
| `assets` | array of `{type, url}` | no | Files to include in the render. `type` ∈ `image \| video \| audio \| font \| csv`. URLs come from `POST /files` or any reachable HTTP(S) URL. |

### `ExternalExportConfig` (each `outputs[]` entry)

All four fields required:

| Field | Allowed values |
|---|---|
| `format` | `mp4` \| `prores` \| `webm` \| `gif` |
| `aspect_ratio` | `16:9` \| `9:16` \| `1:1` \| `4:5` |
| `fps` | `"24"` \| `"25"` \| `"30"` \| `"60"` (string, not number) |
| `resolution` | `360p` \| `480p` \| `720p` \| `1080p` \| `4k` |

Sensible default (per docs): `{ "format": "mp4", "aspect_ratio": "16:9", "fps": "30", "resolution": "1080p" }`.

### Minimal example request

```http
POST https://api.hera.video/v1/videos
x-api-key: <HERA_API_KEY>
Content-Type: application/json
```

```json
{
  "prompt": "A spinning rainbow wheel.",
  "duration_seconds": 8,
  "outputs": [
    {
      "format": "mp4",
      "aspect_ratio": "16:9",
      "fps": "30",
      "resolution": "1080p"
    }
  ]
}
```

### Multi-output + assets example

```json
{
  "prompt": "Animated explainer of Q1 revenue, opening with a punchy headline card, then bar chart, then logo end card. Energetic, optimistic, brand-aligned.",
  "duration_seconds": 20,
  "style_id": "sty_brand_optimistic",
  "reference_image_urls": [
    "https://api.hera.video/v1/files/.../logo.png",
    "https://api.hera.video/v1/files/.../hero.jpg"
  ],
  "assets": [
    { "type": "csv",   "url": "https://api.hera.video/v1/files/.../q1_revenue.csv" },
    { "type": "audio", "url": "https://api.hera.video/v1/files/.../voiceover.mp3" },
    { "type": "font",  "url": "https://api.hera.video/v1/files/.../brand.woff2" }
  ],
  "outputs": [
    { "format": "mp4", "aspect_ratio": "16:9", "fps": "30", "resolution": "1080p" },
    { "format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p" },
    { "format": "mp4", "aspect_ratio": "1:1",  "fps": "30", "resolution": "1080p" }
  ]
}
```

### Response — `CreateVideoOutput` (200 OK)

```json
{
  "video_id": "vid_abcde12345",
  "project_url": "https://app.hera.video/projects/vid_abcde12345"
}
```

`project_url` is optional. `video_id` is the handle for polling.

---

## 4. `GET /videos/{video_id}` — poll status

### Path params

| Param | Type | Notes |
|---|---|---|
| `video_id` | string | The ID returned from `POST /videos`. |

### Response — `GetVideoResponse` (200 OK)

```json
{
  "video_id": "vid_abcde12345",
  "project_url": "https://app.hera.video/projects/vid_abcde12345",
  "status": "in-progress",
  "outputs": [
    {
      "status": "in-progress",
      "config": {
        "format": "mp4",
        "aspect_ratio": "16:9",
        "fps": "30",
        "resolution": "1080p"
      },
      "file_url": null
    }
  ]
}
```

Status enum (`ExternalExportStatusEnum`):

- `in-progress` — still rendering
- `success` — done, `file_url` populated
- `failed` — render errored, `error` field populated on the entry

A job has a top-level `status`, and **each entry in `outputs[]` has its own `status`** — different output configs can succeed and fail independently. Treat per-output status as the source of truth for "is this file ready"; treat the top-level `status` as a roll-up.

### Success example

```json
{
  "video_id": "vid_abcde12345",
  "project_url": "https://app.hera.video/projects/vid_abcde12345",
  "status": "success",
  "outputs": [
    {
      "status": "success",
      "config": { "format": "mp4", "aspect_ratio": "16:9", "fps": "30", "resolution": "1080p" },
      "file_url": "https://cdn.hera.video/renders/vid_abcde12345/16x9.mp4"
    },
    {
      "status": "success",
      "config": { "format": "mp4", "aspect_ratio": "9:16", "fps": "30", "resolution": "1080p" },
      "file_url": "https://cdn.hera.video/renders/vid_abcde12345/9x16.mp4"
    }
  ]
}
```

### Failure example

```json
{
  "video_id": "vid_abcde12345",
  "status": "failed",
  "outputs": [
    {
      "status": "failed",
      "config": { "format": "mp4", "aspect_ratio": "16:9", "fps": "30", "resolution": "1080p" },
      "file_url": null,
      "error": "Asset URL unreachable: https://example.com/missing.csv"
    }
  ]
}
```

### `404` — unknown video

```json
{ "error": "Video/job not found" }
```

### Polling guidance

The docs don't pin a specific polling interval. The standard pattern for async render jobs (and the pattern OpenAI's video API recommends as a comparable) is **poll every 10–20 seconds, with exponential backoff after a few minutes**. Stop polling on `success` or `failed`. Don't poll faster than 1 Hz — there's no benefit and you'll burn rate limit headroom.

---

## 5. `POST /files` — upload an asset

Hosts a file behind a public URL you can pass into `POST /videos` (`reference_image_url`, `reference_image_urls`, `reference_video_url`, or any `assets[].url`).

### Request

```http
POST https://api.hera.video/v1/files
x-api-key: <HERA_API_KEY>
Content-Type: multipart/form-data
```

Form field:

| Field | Type | Required |
|---|---|---|
| `file` | binary | yes |

### Supported types

| Category | Extensions |
|---|---|
| Images | PNG, JPEG, GIF, SVG, WebP, BMP |
| Videos | MP4, MPEG, WebM, MOV, AVI, FLV, MPG, WMV, 3GP |
| Audio | MP3, WAV, AAC |
| Fonts | TTF, OTF, EOT, WOFF, WOFF2 |
| Data | CSV |

**Max size: 10 MB per file.** Larger files are rejected with `400`.

### Success response — `UploadFileOutput` (200 OK)

```json
{
  "url": "https://your-supabase-url.supabase.co/storage/v1/object/public/images/api-uploads/abc123.png"
}
```

(URLs in practice are Supabase-backed; treat them as opaque public URLs.)

### Error response (400)

```json
{ "error": "Unsupported file type: text/plain" }
```

Triggered by missing file, unsupported MIME, or file > 10 MB.

### `curl` example

```bash
curl -X POST https://api.hera.video/v1/files \
  -H "x-api-key: $HERA_API_KEY" \
  -F "file=@./logo.png"
```

---

## 6. End-to-end workflow

Canonical create → poll → download flow.

```text
1. (optional) POST /files for each local asset       → { url }
2. POST /videos with prompt + outputs + asset URLs   → { video_id }
3. Loop: GET /videos/{video_id} every ~10–20s
       until status == "success" or "failed"
4. On success, read outputs[i].file_url for each rendered config
5. Stream/download/proxy the file_url to the client
```

Python sketch (using `httpx`, matching this repo's conventions):

```python
import httpx, asyncio
from src.logger import log

API = "https://api.hera.video/v1"
HEADERS = {"x-api-key": HERA_API_KEY}

async def render(prompt: str, duration: int = 10) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as http:
        create = await http.post(
            f"{API}/videos",
            json={
                "prompt": prompt,
                "duration_seconds": duration,
                "outputs": [
                    {"format": "mp4", "aspect_ratio": "16:9",
                     "fps": "30", "resolution": "1080p"}
                ],
            },
            headers=HEADERS,
        )
        create.raise_for_status()
        video_id = create.json()["video_id"]
        log.info("hera.create", video_id=video_id)

        while True:
            status_res = await http.get(f"{API}/videos/{video_id}", headers=HEADERS)
            status_res.raise_for_status()
            body = status_res.json()
            if body["status"] == "success":
                return [o["file_url"] for o in body["outputs"] if o["file_url"]]
            if body["status"] == "failed":
                errors = [o.get("error") for o in body["outputs"] if o["status"] == "failed"]
                raise RuntimeError(f"Hera render failed: {errors}")
            await asyncio.sleep(10)
```

---

## 7. MCP server

Hera ships an HTTP-transport MCP server. Use this when an AI assistant should call Hera directly without going through your own backend.

| | |
|--|--|
| Endpoint | `https://mcp.hera.video/mcp` |
| Transport | HTTP |
| Auth | `x-api-key: <HERA_API_KEY>` header |
| Supported clients | Claude Code, Codex, Cursor, VS Code, any MCP-compatible client |

### Install (Claude Code)

```bash
claude mcp add --transport http hera https://mcp.hera.video/mcp \
  --header "x-api-key: YOUR_API_KEY"
```

### Generic MCP client config

```json
{
  "hera": {
    "url": "https://mcp.hera.video/mcp",
    "type": "http",
    "headers": {
      "x-api-key": "YOUR_API_KEY"
    }
  }
}
```

### Tools exposed

The MCP server is a 1:1 wrapper of the REST API surface — three tools:

| Tool | Maps to | Purpose |
|---|---|---|
| `create_video` | `POST /videos` | Queue a render job from prompt + outputs config. |
| `get_video` | `GET /videos/{video_id}` | Check job status, fetch download URLs. |
| `upload_file` | `POST /files` | Upload an asset for use in `create_video`. |

#### `create_video`

- Required: `prompt` (string), `outputs` (1–10 `ExternalExportConfig`).
- Optional: `reference_image_url`, `reference_image_urls` (max 5), `reference_video_url`, `duration_seconds` (1–60), `style_id`, `parent_video_id`, `assets[]`.
- Returns: `{ video_id, project_url? }`.

#### `get_video`

- Required: `video_id` (string).
- Returns: `{ video_id, status, project_url?, outputs[] }`.

#### `upload_file`

- Required: `url` (HTTP(S) URL **or local file path** — the MCP server fetches/reads and uploads it).
- Optional: `file_name`.
- Same supported types and 10 MB cap as `POST /files`.
- Returns: hosted URL.

### When to use MCP vs the REST API in this repo

This repo's architecture (FastAPI backend proxying Hera) is **not** the MCP path. We talk to the REST API directly so we can keep `HERA_API_KEY` server-side and add our own agent layer (preset selection, prompt rewriting, decision rationale). The MCP server is useful for:

- Rapid prototyping in Claude Code/Cursor without a backend
- Letting an external assistant generate variations
- Demos

If we ever expose Hera to a client-side AI assistant, route through MCP — never put the API key in the browser.

---

## 8. Hera app (`app.hera.video`)

Auth-gated, no public docs. What's known from the public marketing page and the API:

- It's where users sign in, see projects, and get an API key.
- Each created job has a `project_url` pointing back to it (e.g. `app.hera.video/projects/<video_id>`) — useful as a "view in Hera" link in our UI.
- Default rendering canvas is 16:9, 15s.
- "Hundreds of templates" are browseable; a template's ID can be passed as `parent_video_id` to start from it. The exact template IDs are not enumerated in the public API; users typically copy them from the app or via remix.

---

## 9. Reference: enums and limits in one place

```text
Format          mp4 | prores | webm | gif
Aspect ratio    16:9 | 9:16 | 1:1 | 4:5
FPS (string)    "24" | "25" | "30" | "60"
Resolution      360p | 480p | 720p | 1080p | 4k
Duration        1–60 seconds
Outputs/job     1–10
Reference imgs  up to 5 (use reference_image_urls)
Asset types     image | video | audio | font | csv
File upload     ≤ 10 MB, multipart/form-data, single file per request
Status          in-progress | success | failed
```

---

## 10. Errors observed in the spec

| Endpoint | Status | Body shape |
|---|---|---|
| `POST /videos` | 200 | `{ video_id, project_url? }` |
| `GET /videos/{id}` | 200 | `GetVideoResponse` |
| `GET /videos/{id}` | 404 | `{ error: "Video/job not found" }` |
| `POST /files` | 200 | `{ url }` |
| `POST /files` | 400 | `{ error: "Unsupported file type: ..." }` |

The public spec documents only these. Other failure modes (auth errors, rate limits, server errors) are not documented but should be assumed possible — defensively treat any non-2xx as actionable. **Rate limits are not published.**

---

## 11. Things the docs do *not* tell you (open questions)

These are gaps an agent should know about so it doesn't fabricate behavior:

- No published rate limits — back off on 429s if you see them.
- No webhook/callback mechanism in the public spec — polling is the only completion mechanism.
- `style_id` and `parent_video_id` are accepted, but there is no public list of valid IDs. They come from the Hera app or from previously created jobs.
- No documented prompt length limit. Be sensible (a few thousand chars max).
- No documented behavior for partial failures within a multi-output job — assume each `outputs[i]` succeeds/fails independently and handle accordingly.
- The `project_url` field is marked optional in the schema; don't depend on it being present.
- File uploads are stored on what appears to be a Supabase-backed CDN. URLs are public; treat anything you upload as effectively public.

---

## 12. Cheat sheet for the agent layer in this repo

When `backend/src/agent/` gets built, these are the levers it actually has:

- **`prompt`** — the largest editorial surface. The agent's "opinions" mostly live here.
- **`style_id`** — pick a visual style based on context (audience, brand, platform).
- **`parent_video_id`** — start from a known-good template instead of from scratch when applicable.
- **`outputs[]`** — multi-aspect renders for cross-platform delivery (e.g. 16:9 for YouTube, 9:16 for Reels/TikTok, 1:1 for IG feed) in a single job.
- **`duration_seconds`** — pick by platform: ≤15s for stop-scroll social, 20–40s for product launch, 30–60s for explainers.
- **`reference_image_urls`** + **`assets[]`** — feed brand artifacts (logo, palette, fonts) and data (CSV for charts) so the render is on-brand and on-fact.

Everything else is fixed by the API. The agent's value-add is making these choices well, with reasons, given the user's input.
