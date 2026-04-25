# berlin-hackathon-2026-hera

Hackathon entry for **Berlin Tech Europe Hackathon 2026**, **Hera track** (AI Agents for Video Generation).

## The challenge

Generating a video is easy. Image, video, and language models can produce an asset in seconds. The hard part is deciding what the asset should look like: the hook, the angle, the pacing, the emphasis. That's what separates work that lands from work that doesn't.

So this isn't a "generate a video" tool. It's a **creative agent with opinions**. Beliefs about what makes a launch feel exciting, a stance on what makes a social post worth watching, a view on how to compress a dense document into something a person actually wants to sit through. Without those opinions, the output is slop.

## What we're building

> **Problem & agent POV:** TBD. See `CLAUDE.md` for the candidate directions.

Once locked, the agent will:

1. Take a user input (a product, a brief, a document, depending on direction).
2. Make editorial decisions on its own, guided by presets and tastes we encode.
3. Drive the [Hera](https://hera.video) motion graphics API to produce the output.
4. Be able to explain *what* it decided and *why*.

## Stack

- **Frontend:** Vite + React + TypeScript (`frontend/`)
- **Backend:** FastAPI + httpx (`backend/`), Python 3.11+ via [uv](https://docs.astral.sh/uv/)
- **Video pipeline:** Hera REST API at `https://api.hera.video/v1`
- **Auth model:** the Hera API key lives only on the backend. The browser only talks to the FastAPI proxy.

## Setup

```bash
cp .env.example .env       # paste your HERA_API_KEY (get one at https://app.hera.video/)
make install               # backend (uv sync) + frontend (bun install)
make dev                   # backend :8000 + frontend :5173
```

Open http://localhost:5173.

## Layout

```
backend/
  src/
    main.py          FastAPI app, Hera proxy, Pydantic models
    logger.py        shared logger (writes backend/logs/app.log)
    agent/           agent logic (presets, decisions, prompts) — to be added
  pyproject.toml
frontend/
  src/
    App.tsx          single-page UI: prompt -> submit -> poll -> render
    App.css
.env                 secrets (gitignored)
.env.example         template
Makefile
```

## Make targets

| Target | What it does |
|--------|--------------|
| `make install` | Install backend (`uv sync`) and frontend (`bun install`) deps |
| `make dev-backend` | Run FastAPI on `:8000` |
| `make dev-frontend` | Run Vite on `:5173` |
| `make dev` | Run both in parallel |
| `make lint` | `ruff check` (backend) + `tsc --noEmit` (frontend) |
| `make format` | `ruff format` + Prettier |
| `make clean` | Remove `.venv`, `node_modules`, build output, and logs |

## Hera reference

- API: https://docs.hera.video/api-reference/introduction
- MCP server: https://docs.hera.video/mcp-server
- App / API key: https://app.hera.video/

## Team plan

Tracking in Notion: https://www.notion.so/karlvillanueva/Berlin-Hackathon-2026-34d942178bfd8059b2ecc0b41790cf44?source=copy_link
