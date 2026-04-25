# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/). Types map to conventional commits.

## 2026-04-25

### feat: build Airbnb→video MVP (4-screen flow + agent + endpoints)
- **Backend agent module** (`backend/src/agent/`): `models.py`, `classifier.py`, `image_scorer.py`, `prompt_builder.py`, `orchestrator.py`, `fixture_loader.py`, plus `fixtures/kreuzberg-loft.json` (synthetic Berlin Kreuzberg listing with 8 photos and realistic copy).
- **Editorial classifier** uses Claude Sonnet 4.6 via Anthropic SDK with forced `tool_use` for structured JSON output. Returns `{vibes, hook, pacing, angle, background}` — four editorial decisions, not a single category pick.
- **New endpoints** in `backend/src/main.py`: `POST /api/listing` (load fixture + run agent → return listing + decision) and `POST /api/generate` (submit Hera job using pre-computed decision). Existing `/api/videos/{id}` polling unchanged.
- **Frontend 4-screen flow** (`frontend/src/`): `App.tsx` state machine (idle → reviewing → generating → done + error), polling with 5s interval and 3-min cap. Components: `Header`, `UrlInput`, `AttributeCard`, `StatusRow`, `VideoPlayer` (9:16), `RationaleRail`, `ErrorState`. Typed `api/client.ts` against the locked contract.
- **Tailwind v4** wired via `@tailwindcss/vite` plugin with Inter font from Google Fonts. Monochrome design language (white/black/gray, 1px borders, sharp corners) per `hera-video-hackathon.pen`.
- **Vite/plugin-react fix**: downgraded `vite` to `^7` and `@vitejs/plugin-react` to `^5` to resolve a Vite 8 + plugin-react 6 regression where the React Refresh preamble wasn't injected. Added explicit `import '@vitejs/plugin-react/preamble'` in `main.tsx` as a belt-and-braces guard.
- **Smoke test passed**: `POST /api/listing` returns rich, opinionated editorial decisions (e.g. "Sell the Kreuzberg lifestyle fantasy — the rooftop sunset, the corner espresso, the canal bike ride — not the square footage").
- Added `anthropic>=0.40.0` dependency in `backend/pyproject.toml`.

### feat: scaffold Hera probes and local API docs
- Added `HERA.md` — full local copy of Hera API + MCP docs (endpoints, schemas, enums, agent levers) so the agent can read it without re-fetching.
- Added `backend/scripts/probe_hera.py` and `backend/scripts/probe_scrape.py` — exploratory probes against the Hera API and a Playwright-based scrape.
- Added `playwright>=1.49` dependency in `backend/pyproject.toml` (lockfile updated).
- `backend/src/main.py` now also loads `../credentials/credentials.env` and reads `ANTHROPIC_HACKATHON_KEY` from env.
- Updated `CLAUDE.md` to point at the local `HERA.md` first, upstream docs second.
- Continued design work in `hera-video-hackathon.pen`.

### chore: add hackathon design file and ignore tool artifacts
- Added `hera-video-hackathon.pen` — Pencil design source for the Hera hackathon UI.
- Hardened `.gitignore` to exclude `.entire/`, `design-extract-output/`, `/credentials`, and `/credentials.env`.
