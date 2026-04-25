# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/). Types map to conventional commits.

## 2026-04-25

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
