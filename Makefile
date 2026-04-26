.PHONY: install dev dev-backend dev-frontend phase1-core lint format clean

install:
	cd backend && uv sync
	cd frontend && bun install

dev-backend:
	cd backend && uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && bun run dev

dev:
	@echo "Starting backend (8000) and frontend (5173)..."
	@(cd backend && uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000) & \
	 (cd frontend && bun run dev) & \
	 wait

# Print ICP, location, reviews, and visual_system for a fixture (needs GCP_* in .env).
# Example: make phase1-core URL=https://www.airbnb.com/rooms/kreuzberg-loft-demo
URL ?= https://www.airbnb.com/rooms/kreuzberg-loft-demo
phase1-core:
	@cd backend && \
	if command -v uv >/dev/null 2>&1; then \
		PYTHONPATH=. uv run python scripts/print_phase1_core.py $(URL); \
	elif test -x .venv/bin/python; then \
		PYTHONPATH=. .venv/bin/python scripts/print_phase1_core.py $(URL); \
	else \
		echo "Run 'make install' (or use uv) so Python deps exist, then re-run." >&2; \
		exit 1; \
	fi

lint:
	cd backend && uv run ruff check .
	cd frontend && bun run tsc --noEmit

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && bunx prettier --write src

clean:
	rm -rf backend/.venv backend/.ruff_cache backend/__pycache__
	rm -rf frontend/node_modules frontend/dist
	rm -rf logs
