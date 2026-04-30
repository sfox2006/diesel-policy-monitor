"""
Central configuration — loaded once at import time.
All values come from environment variables (or .env file).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_int(key: str, default: int = 0) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default


def _get_float(key: str, default: float = 0.0) -> float:
    try:
        return float(_get(key, str(default)))
    except ValueError:
        return default


# ── SMTP ──────────────────────────────────────────────────────────────────────
SMTP_HOST: str = _get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = _get_int("SMTP_PORT", 587)
SMTP_USER: str = _get("SMTP_USER")
SMTP_PASSWORD: str = _get("SMTP_PASSWORD")
EMAIL_FROM: str = _get("EMAIL_FROM", "samfoxbartending@gmail.com") or SMTP_USER
EMAIL_TO: list[str] = [
    e.strip() for e in _get("EMAIL_TO", "sam.fox@mandalapartners.com").split(",") if e.strip()
]

# ── Paths ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR: Path = _ROOT / _get("OUTPUT_DIR", "output")
DEEP_DIVES_DIR: Path = OUTPUT_DIR / "deep_dives"
DB_PATH: Path = _ROOT / _get("DB_PATH", "policy_monitor.db")
LOG_DIR: Path = _ROOT / _get("LOG_DIR", "logs")

# ── Behaviour ─────────────────────────────────────────────────────────────────
MAX_ITEMS_PER_RUN: int = _get_int("MAX_ITEMS_PER_RUN", 200)
TOP_DEVELOPMENTS: int = _get_int("TOP_DEVELOPMENTS", 5)
WATCHLIST_ITEMS: int = _get_int("WATCHLIST_ITEMS", 3)
TLDR_BULLETS: int = _get_int("TLDR_BULLETS", 6)

# Drop scored items below this threshold before writing the briefing.
# This keeps broad but weakly related feed items out of the final email.
MIN_RELEVANCE_SCORE: float = _get_float("MIN_RELEVANCE_SCORE", 25.0)

# Items with a publish date older than this are dropped before ranking.
# HTML-scraped items with no publish date are kept (age cannot be determined).
# Set to 0 to disable the filter entirely.
MAX_ITEM_AGE_HOURS: int = _get_int("MAX_ITEM_AGE_HOURS", 24)

# Source profile:
# - fuel_policy: default focused crawl for diesel/fuel and official policy briefings.
# - all: legacy full catalogue, including broad industry and union sources.
SOURCE_PROFILE: str = _get("SOURCE_PROFILE", "fuel_policy").lower()

# Day of week for the weekly outlook email (0=Monday … 6=Sunday). Default: 6 (Sunday).
WEEKLY_DAY_OF_WEEK: int = _get_int("WEEKLY_DAY_OF_WEEK", 6)

# ── HTTP ──────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT: int = _get_int("REQUEST_TIMEOUT", 8)
REQUEST_DELAY: float = _get_float("REQUEST_DELAY", 0.2)
USER_AGENT: str = _get(
    "USER_AGENT", "PolicyMonitor/1.0 (research@mandalapartners.com)"
)

# ── Ensure output directories exist ──────────────────────────────────────────
for _d in (OUTPUT_DIR, DEEP_DIVES_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)
