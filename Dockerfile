# syntax=docker/dockerfile:1.7

# ---- Frontend build stage ----
FROM node:22-slim AS fe-builder
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# VITE_* envs need to be available at build time so they get embedded into the bundle.
ARG VITE_BACKEND_URL=
ARG VITE_SUPABASE_URL=
ARG VITE_SUPABASE_ANON_KEY=
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL \
    VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
RUN npm run build  # → /fe/dist

# ---- Backend stage ----
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble AS runtime
WORKDIR /app

# uv: faster Python dependency installer
RUN pip install --no-cache-dir uv

# Install Python deps first (better layer caching).
# .python-version is copied so uv auto-downloads the pinned interpreter (3.14)
# rather than falling back to the system Python (3.12 on noble) and breaking
# the locked wheel set.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev

# Backend source
COPY backend/src/ ./src/
COPY backend/scripts/entrypoint.sh ./entrypoint.sh
COPY supabase/migrations/ ./migrations/
RUN chmod +x ./entrypoint.sh

# Frontend dist → ./static so main.py's StaticFiles mount picks it up.
COPY --from=fe-builder /fe/dist ./static/

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["./entrypoint.sh"]
