# CLAUDE.md

Hackathon project: video generation tool wrapping the Hera motion-graphics API.

## External References

- **Hackathon plan (Notion):** https://www.notion.so/karlvillanueva/Berlin-Hackathon-2026-34d942178bfd8059b2ecc0b41790cf44?source=copy_link
- **Hera API Reference:** https://docs.hera.video/api-reference/introduction
- **Hera MCP Server:** https://docs.hera.video/mcp-server
- **Hera App:** https://app.hera.video/

## Architecture

- `frontend/` — Vite + React + TypeScript single-page app. Calls only `backend/` over `VITE_BACKEND_URL`.
- `backend/` — FastAPI app. Holds the `HERA_API_KEY`. Proxies to `https://api.hera.video/v1`.

The Hera API key never reaches the browser. Don't import it client-side.

## Hera API quick reference

| | |
|--|--|
| Base URL | `https://api.hera.video/v1` |
| Auth header | `x-api-key: $HERA_API_KEY` |
| Create video | `POST /videos` → `{ video_id, project_url? }` |
| Poll status | `GET /videos/{video_id}` → `{ status: "in-progress" \| "success" \| "failed", outputs[] }` |
| Upload asset | `POST /files` |

`POST /videos` minimum body:
```json
{
  "prompt": "string",
  "outputs": [{"format": "mp4", "aspect_ratio": "16:9", "fps": "30", "resolution": "1080p"}]
}
```

On success, the rendered file is at `outputs[0].file_url` of the GET response.

## Key Commands

```bash
make install          # uv sync + bun install
make dev              # backend :8000 + frontend :5173
make dev-backend
make dev-frontend
make lint             # ruff + tsc
make format           # ruff format + prettier
```

## Conventions

- Backend logger: `from src.logger import log` (writes to `logs/app.log`).
- Never log secret values.
- Pydantic models for every request/response body.
- Frontend env vars must be prefixed `VITE_` to be exposed to the bundle.
