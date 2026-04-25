"""Shared logging config. Usage: from src.logger import log"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log = logging.getLogger("hera-backend")
log.setLevel(logging.DEBUG)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(_fmt)

_file = logging.FileHandler(LOG_DIR / "app.log")
_file.setLevel(logging.DEBUG)
_file.setFormatter(_fmt)

if not log.handlers:
    log.addHandler(_console)
    log.addHandler(_file)
