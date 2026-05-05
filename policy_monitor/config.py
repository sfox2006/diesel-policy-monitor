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


DEFAULT_X_ACCOUNT_HANDLES = (
    "AlboMP,JEChalmers,SenatorWong,MadeleineMHKing,ayrestim,"
    "senator_farrell,PatConroy1,murraywatt,CatherineKingMP,AngusTaylorMP,"
    "ACCCgovau,dfat,mineralscouncil,Nationalfarmers,au_energy_prod,"
    "Johnkehoe23,angelamacd,NickToscano1,JavierBlas,IEA,FatihBirol,"
    "Opecsecretariat,Hellenicship,realDonaldTrump,CENTCOM,araghchi,"
    "Meti_nippon,JOGMEC_JP,takaichi_sanae,NikkeiAsia,AnwarIbrahim,"
    "Lawrencewongst,MTI_sg,MFAsg,channelnewsasia,Bangkokpostnews,MFAThai,"
    "Reuters,abcpolitics,financialreview,AJEnglish,FTenergy,WSJenergy,australian"
)

DEFAULT_X_PERSON_ACCOUNT_HANDLES = (
    "AlboMP,JEChalmers,SenatorWong,MadeleineMHKing,ayrestim,"
    "senator_farrell,PatConroy1,murraywatt,CatherineKingMP,AngusTaylorMP,"
    "Johnkehoe23,angelamacd,NickToscano1,JavierBlas,FatihBirol,"
    "realDonaldTrump,araghchi,takaichi_sanae,AnwarIbrahim,Lawrencewongst"
)

DEFAULT_X_MEDIA_ACCOUNT_HANDLES = (
    "Hellenicship,NikkeiAsia,channelnewsasia,Bangkokpostnews,Reuters,"
    "abcpolitics,financialreview,AJEnglish,FTenergy,WSJenergy,australian"
)

DEFAULT_X_KEYWORDS = (
    "diesel,petrol,gasoline,gasoil,fuel,refinery,refineries,"
    "fuel security,Strait of Hormuz,Hormuz,fuel reserve,"
    "petroleum reserve,fuel shortage"
)


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

# X / social monitoring. Uses twitterapi.io account timelines when TWITTERAPI_IO_KEY is set.
TWITTERAPI_IO_KEY: str = _get("TWITTERAPI_IO_KEY") or _get("X_API_KEY")
X_ACCOUNT_HANDLES: list[str] = [
    handle.strip().lstrip("@")
    for handle in (_get("X_ACCOUNT_HANDLES") or DEFAULT_X_ACCOUNT_HANDLES).split(",")
    if handle.strip()
]
X_KEYWORDS: list[str] = [
    term.strip()
    for term in (_get("X_KEYWORDS") or DEFAULT_X_KEYWORDS).split(",")
    if term.strip()
]
X_MAX_RESULTS: int = max(10, min(_get_int("X_MAX_RESULTS", 25), 500))
X_MAX_MATCHES_PER_ACCOUNT: int = max(1, min(_get_int("X_MAX_MATCHES_PER_ACCOUNT", 500), 500))
X_PERSON_ACCOUNT_HANDLES: list[str] = [
    handle.strip().lstrip("@")
    for handle in (_get("X_PERSON_ACCOUNT_HANDLES") or DEFAULT_X_PERSON_ACCOUNT_HANDLES).split(",")
    if handle.strip()
]
X_MEDIA_ACCOUNT_HANDLES: list[str] = [
    handle.strip().lstrip("@")
    for handle in (_get("X_MEDIA_ACCOUNT_HANDLES") or DEFAULT_X_MEDIA_ACCOUNT_HANDLES).split(",")
    if handle.strip()
]
X_DEFAULT_SCAN_LIMIT: int = max(1, min(_get_int("X_DEFAULT_SCAN_LIMIT", 25), 500))
X_PERSON_SCAN_LIMIT: int = max(1, min(_get_int("X_PERSON_SCAN_LIMIT", 25), 500))
X_MEDIA_SCAN_LIMIT: int = max(1, min(_get_int("X_MEDIA_SCAN_LIMIT", 125), 500))
X_LOOKBACK_HOURS: int = max(1, min(_get_int("X_LOOKBACK_HOURS", 24), 168))
X_INCLUDE_RETWEETS: bool = _get("X_INCLUDE_RETWEETS", "false").lower() in {"1", "true", "yes"}
X_SECTION_ITEMS: int = max(0, _get_int("X_SECTION_ITEMS", 8))

# ── Ensure output directories exist ──────────────────────────────────────────
for _d in (OUTPUT_DIR, DEEP_DIVES_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)
