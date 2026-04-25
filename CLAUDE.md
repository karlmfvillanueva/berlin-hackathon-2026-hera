# CLAUDE.md

Project context for Claude Code working in this repo.

## What this is

Hackathon entry for **Berlin Tech Europe Hackathon 2026**, **Hera track** (AI Agents for Video Generation). Track prize: AirPod Pros (1x per member).

Hera is an AI motion graphics startup. The challenge isn't "generate a video", it's "build a creative agent that has opinions about what the video should be." Just generating output without editorial judgment produces slop. The agent must make decisions about hook, angle, pacing, emphasis, and explain why.

Source: https://hera.video/?utm_source=luma

## Problem & Agent POV (TBD)

This is the central design decision and is not yet locked. Pick one of the Hera-suggested directions or define our own:

1. **Product launch agent.** Generates launch videos good enough to go viral, without the user needing to know how product launches work. Agent has opinions about hook structure, what to show first, pacing for attention.
2. **Social content agent.** Produces social posts that earn the stop-scroll. Opinions about format per platform, hook windows, and visual density.
3. **PDF to explainer.** Takes a long document and turns it into a watchable explainer with voice over. Opinions about what to cut, what to emphasize, and how to structure narrative.
4. **Our own direction.** TBD.

Until this is decided, treat the codebase as a generic Hera proxy. Once decided, the agent's beliefs/presets/taste live in `backend/src/agent/` (not yet created).

## External references

- **Hackathon plan (Notion):** https://www.notion.so/karlvillanueva/Berlin-Hackathon-2026-34d942178bfd8059b2ecc0b41790cf44?source=copy_link
- **Local Hera reference:** [`HERA.md`](./HERA.md) — full local copy of API + MCP docs (endpoints, schemas, enums, example payloads, agent levers). Read this instead of re-fetching the docs.
- **Hera API reference (upstream):** https://docs.hera.video/api-reference/introduction
- **Hera MCP server (upstream):** https://docs.hera.video/mcp-server
- **Hera app:** https://app.hera.video/

## Architecture

- `frontend/` Vite + React + TypeScript single page app. Talks only to `backend/` over `VITE_BACKEND_URL`.
- `backend/` FastAPI app. Holds `HERA_API_KEY`. Proxies to `https://api.hera.video/v1`.
- The Hera API key never reaches the browser. Don't import it client-side, don't expose it via any `VITE_*` variable.

## Hera API quick reference

| | |
|--|--|
| Base URL | `https://api.hera.video/v1` |
| Auth header | `x-api-key: $HERA_API_KEY` |
| Create video | `POST /videos` returns `{ video_id, project_url? }` |
| Poll status | `GET /videos/{video_id}` returns `{ status, outputs[] }` where `status` is `in-progress` \| `success` \| `failed` |
| Upload asset | `POST /files` |

`POST /videos` minimum body:
```json
{
  "prompt": "string",
  "outputs": [{"format": "mp4", "aspect_ratio": "16:9", "fps": "30", "resolution": "1080p"}]
}
```

Optional fields: `duration_seconds` (1 to 60), `style_id`, `parent_video_id`, `reference_image_url`, `reference_image_urls` (max 5), `reference_video_url`, `assets[]` (image/video/audio/font/csv).

On success, the rendered file lives at `outputs[0].file_url` in the GET response.

## Key commands

```bash
make install          # uv sync + bun install
make dev              # backend :8000 + frontend :5173
make dev-backend
make dev-frontend
make lint             # ruff + tsc
make format           # ruff format + prettier
```

## Conventions

- Backend logger: `from src.logger import log`. Writes to `backend/logs/app.log`.
- Never log secret values, including any part of `HERA_API_KEY`.
- Every request/response body uses a Pydantic model.
- Frontend env vars must be prefixed `VITE_` to reach the bundle. Never put secrets there.
- Place agent logic (prompt construction, preset selection, decision rationale) under `backend/src/agent/`. Keep the proxy layer in `backend/src/main.py` thin.
