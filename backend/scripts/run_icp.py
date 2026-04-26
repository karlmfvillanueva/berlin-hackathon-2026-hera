"""Run the ICP Classifier on a JSON scrape file (Airbnb-shaped document).

  cd backend
  PYTHONPATH=. uv run python scripts/run_icp.py
  PYTHONPATH=. uv run python scripts/run_icp.py src/agent/fixtures/property-1.json

Requires ``GCP_PROJECT`` and Vertex ADC (see ``.env.example``)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
for path in (
    _REPO_ROOT / "credentials" / "credentials.env",
    _REPO_ROOT / ".env",
):
    if path.is_file():
        load_dotenv(path)
load_dotenv()

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.agent.icp_classifier import classify_icp  # noqa: E402

_DEFAULT = _BACKEND / "src" / "agent" / "fixtures" / "kreuzberg-loft.json"


def main() -> None:
    path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else _DEFAULT
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        sys.exit(1)
    scrape = json.loads(path.read_text(encoding="utf-8"))
    out = classify_icp(scrape)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
