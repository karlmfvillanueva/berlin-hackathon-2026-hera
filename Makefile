.PHONY: install dev dev-backend dev-frontend lint format clean

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
