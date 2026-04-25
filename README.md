# berlin-hackathon-2026-hera

Video generation tool built on the [Hera](https://hera.video) motion-graphics API. Hackathon project, Berlin 2026.

## Stack

- **Frontend:** Vite + React + TypeScript (`frontend/`)
- **Backend:** FastAPI + httpx + uv (`backend/`)
- **Hera API:** `https://api.hera.video/v1` (key auth via `x-api-key`)

The browser never sees the Hera API key. All Hera calls go through the FastAPI backend.

## Setup

```bash
cp .env.example .env       # then fill in HERA_API_KEY
make install                # installs backend + frontend deps
make dev                    # runs backend (8000) and frontend (5173)
```

Open http://localhost:5173.

## Layout

```
backend/    FastAPI app (src/main.py, src/logger.py)
frontend/   Vite React app (src/App.tsx)
.env        secrets (gitignored)
```

## Make targets

| Target | What it does |
|--------|-------|
| `make install` | Install backend (uv sync) + frontend (bun install) deps |
| `make dev-backend` | Run FastAPI on `:8000` |
| `make dev-frontend` | Run Vite on `:5173` |
| `make dev` | Run both in parallel |
| `make lint` | Ruff (backend) + tsc (frontend) |
| `make format` | Ruff format + prettier |
