#!/usr/bin/env bash
# Container entrypoint. Two responsibilities Railway forces on us:
#   1. Materialise the Google service-account JSON from an env var into a file
#      so Vertex AI ADC can find it. There's no `gcloud auth login` on Railway.
#   2. Bind to the $PORT Railway injects, falling back to 8000 for local docker.
set -euo pipefail

if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS_JSON:-}" && -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  printf '%s' "$GOOGLE_APPLICATION_CREDENTIALS_JSON" > /tmp/gcp-key.json
  export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
  echo "entrypoint: wrote GCP key to $GOOGLE_APPLICATION_CREDENTIALS"
fi

exec uv run uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
