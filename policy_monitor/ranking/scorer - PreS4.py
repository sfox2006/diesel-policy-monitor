"""
Scoring and ranking engine — Australian Diesel Fuel Security edition.

Briefing sections:
  1. Diesel tracker        — reserves, shipments, price, station outages
  2. Supply partners       — Japan, Malaysia, Singapore, South Korea, Thailand
  3. Supply chain          — tankers, terminals, refining, geopolitics
  4. Australia policy      — ministerial, IEA obligations, legislation

Scoring dimensions
──────────────────
1. Source type bonus      primary +20 | secondary +8
2. Topic bonus            matched against source catalogue tags
3. Keyword matches        title + summary scanned against priority patterns
4. Recency bonus          published today +10 | yesterday +5
5. Watchlist flag         upcoming events, deadlines, consultations

Items with zero keyword matches and no topic bonus are suppressed
(score stays at source bonus + recency only, never reaching top 5).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)


# ── Topic bonus — must match topic names used in sources.py exactly ───────────
TOPIC_BONUS: dict[str, float] = {
    "reserves_and_prices":  12.0,   # Section 1 — diesel tracker
    "shipments":            12.0,   # Section 1 — tanker/import data
    "partner_country":      10.0,   # Section 2 — Japan/Malaysia/Singapore/Korea/Thailand
    "supply_disruption":    10.0,   # Section 3 — refinery/route disruptions
    "policy_and_legislation": 8.0,  # Section 4 — ministerial/IEA/bills
}

# ── Priority keyword patterns ──────────────────────────────────────────────────
# Each entry: (regex_pattern, score_weight)
# Matched against (title + " " + summary), case-insensitive.

PRIORITY_PATTERNS: list[tuple[str, float]] = [

    # ── Section 1: Diesel tracker ─────────────────────────────────────────────
    (r"\bdiesel reserve\w*", 15.0),
    (r"\bdays? of (diesel|fuel|reserve|supply)", 15.0),
    (r"\b90.day (reserve|obligation|stockholding)", 15.0),
    (r"\bminimum stockholding obligation|mso\b", 15.0),
    (r"\bfuel stockholding\w*", 14.0),
    (r"\bstrategic (petroleum )?reserve\w*", 14.0),
    (r"\btanker arrival\w*", 13.0),
    (r"\bfuel import terminal\w*", 13.0),
    (r"\bdiesel wholesale price\w*", 12.0),
    (r"\bterminal gate price\w*", 12.0),
    (r"\bstation outage\w*", 12.0),
    (r"\bpetrol station.{0,20}(empty|out of stock|no diesel)", 12.0),
    (r"\bdiesel\b", 10.0),
    (r"\bliquid fuel\w*", 10.0),
    (r"\bfuel securit\w+", 10.0),
    (r"\bpetroleum reserve\w*", 10.0),
    (r"\bfuel shortfall\w*", 13.0),
    (r"\bfuel ship\w*", 12.0),
    (r"\bfuel scheme\w*", 11.0),

    # ── Section 2: Supply partner signals ────────────────────────────────────

    # Japan
    (r"\bjapan.{0,50}(reserve|diesel|fuel|oil|iea|strateg|subsid)", 14.0),
    (r"\bjapan.{0,30}iea collective action", 14.0),
    (r"\bjapan.{0,30}(diesel subsid|fuel subsid)", 13.0),
    (r"\banre\b|agency for natural resources and energy", 13.0),
    (r"\bjogmec\b", 12.0),

    # Malaysia
    (r"\bmalaysia.{0,50}(reserve|diesel|fuel|oil|subsid|export|supply)", 14.0),
    (r"\bpetronas\b", 13.0),
    (r"\bmalaysia.{0,30}(diesel subsid|fuel subsid|price control)", 13.0),
    (r"\bmalaysia.{0,30}export (ban|cap|restrict)", 13.0),

    # Singapore
    (r"\bsingapore.{0,50}(reserve|diesel|fuel|oil|refin|export|australia)", 14.0),
    (r"\bsingapore.{0,30}australia.{0,30}(fuel|oil|supply|agreement|deal)", 15.0),
    (r"\bema singapore|energy market authority", 12.0),
    (r"\bsingapore.{0,30}(bunker|refin|trading hub)", 11.0),

    # South Korea
    (r"\b(south )?korea.{0,50}(reserve|diesel|fuel|oil|export|price cap)", 14.0),
    (r"\bkorea.{0,30}iea collective action", 14.0),
    (r"\bkorea.{0,30}(retail price cap|price control)", 13.0),
    (r"\bkorea.{0,30}export cap\w*", 14.0),
    (r"\bknoc\b|korea national oil", 12.0),

    # Thailand
    (r"\bthailand.{0,50}(reserve|diesel|fuel|oil|export|biodiesel)", 14.0),
    (r"\bptt\b|ptt plc", 13.0),
    (r"\bthailand.{0,30}biodiesel blend", 13.0),
    (r"\bthailand.{0,30}(export ban|ban on export)", 14.0),
    (r"\bthailand.{0,30}oil trader\w*", 13.0),

    # ── Section 3: Supply chain / geopolitical risk ───────────────────────────
    (r"\btanker\w*", 9.0),
    (r"\brefiner\w+", 9.0),
    (r"\bdistillate\w*", 10.0),
    (r"\bfuel import\w*", 11.0),
    (r"\bfuel export\w*", 11.0),
    (r"\bsupply disruption\w*", 12.0),
    (r"\bshipping disruption\w*", 11.0),
    (r"\bsupply chain (disruption|risk|securit)", 11.0),
    (r"\bstrait of malacca|malacca strait", 12.0),
    (r"\bsouth china sea.{0,30}(shipping|supply|oil|fuel)", 12.0),
    (r"\bstrait of hormuz|hormuz", 12.0),
    (r"\bchoke point\w*", 11.0),
    (r"\bport (congestion|disruption|closure)", 10.0),
    (r"\bbotany|geelong|fremantle|brisbane.{0,20}(fuel|terminal|tanker)", 10.0),
    (r"\biea collective action", 14.0),
    (r"\bopec.{0,30}(cut|output|production|supply)", 9.0),
    (r"\bcrude oil.{0,30}(price|supply|disruption)", 8.0),
    (r"\biran.{0,30}(oil|fuel|strait|sanction)", 10.0),
    (r"\bmiddle east.{0,30}(oil|fuel|supply|shipping)", 10.0),

    # ── Section 4: Australia policy response ──────────────────────────────────
    (r"\bchris bowen\b", 13.0),
    (r"\bmadeleine king\b", 13.0),
    (r"\bdon farrell\b", 11.0),
    (r"\bjim chalmers\b", 10.0),
    (r"\banthony albanese.{0,40}(fuel|energy|singapore|oil)", 14.0),
    (r"\bminister (for|of) (energy|resources|fuel|climate)", 12.0),
    (r"\bdccew\b", 12.0),
    (r"\baemo\b", 10.0),
    (r"\baustralia.{0,40}(fuel polic|fuel strateg|fuel plan|fuel secur)", 13.0),
    (r"\baustralia.{0,30}iea obligation\w*", 14.0),
    (r"\baustralia.{0,30}90.day", 14.0),
    (r"\bappropriation.{0,30}fuel securit", 15.0),
    (r"\bfuel security response bill", 15.0),
    (r"\bparliament.{0,20}(fuel|energy|diesel)", 9.0),
    (r"\bsenate.{0,20}(fuel|energy|diesel)", 9.0),
    (r"\baustralia.{0,30}singapore.{0,30}(agree|deal|mou).{0,30}fuel", 15.0),
    (r"\balbanese.{0,30}singapore", 13.0),

    # ── Watchlist / forward-looking ───────────────────────────────────────────
    (r"\bupcoming (review|report|statement|decision)", 5.0),
    (r"\bpublic consultation|call for submissions?", 5.0),
    (r"\bdeadline|due date|closes?\b", 4.0),
    (r"\bscheduled|forthcoming|expected to (publish|announc|release)", 4.0),
    (r"\bcommittee hearing|senate hearing|parliamentary question", 5.0),
    (r"\bbudget (2026|2027).{0,20}(fuel|energy|reserve|diesel)", 6.0),
    (r"\biea collective action", 6.0),
    (r"\bexport (ban|cap|restrict).{0,20}(diesel|fuel|refined)", 6.0),
]

# ── Negative keywords — suppress clear noise ───────────────────────────────────
NEGATIVE_PATTERNS: list[tuple[str, float]] = [
    (r"\belectric vehicle\b|ev charging\b", -8.0),
    (r"\bbioethanol\b", -6.0),
    (r"\bfuel voucher|petrol station promot", -10.0),
    (r"\bpetrol price watch|weekly petrol price", -6.0),
    (r"\bwind (farm|turbine|power)\b", -5.0),
    (r"\bsolar (panel|farm|power)\b", -5.0),
    (r"\bfashion|clothing|apparel|layered piece\w*", -20.0),
    (r"\bnasa\b.{0,30}(photo|image|picture|moon|space|artemis)", -20.0),
    (r"\bcyclone|hurricane|typhoon", -10.0),
    (r"\bcorrupt\w*|obeid|prosecution|criminal charge", -15.0),
    (r"\bammonia\b", -8.0),
    (r"\bgreen hydrogen|green ammonia", -10.0),
    (r"\belectricit\w+ disconnection", -8.0),
    (r"\bpodcast\b", -10.0),
    (r"\bbitcoin|etf|crypto\w*", -10.0),
    (r"\btourism|restaurant\w*|visitor\w*", -10.0),
]

# ── Watchlist patterns ────────────────────────────────────────────────────────
WATCHLIST_PATTERNS: list[str] = [
    r"\bupcoming (review|report|statement|decision)",
    r"\bpublic consultation|call for submissions?",
    r"\bdeadline|due date|closes?\b",
    r"\bscheduled|forthcoming|expected to (publish|announc|release)",
    r"\bcommittee hearing|senate hearing|parliamentary question",
    r"\bbudget (2026|2027).{0,20}(fuel|energy|reserve|diesel)",
    r"\bappropriation.{0,30}fuel securit",
    r"\biea collective action",
    r"\bexport (ban|cap|restrict).{0,20}(diesel|fuel|refined)",
]


def _compile_weighted(patterns: list[tuple[str, float]]) -> list[tuple[re.Pattern, float]]:
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_COMPILED_PRIORITY = _compile_weighted(PRIORITY_PATTERNS)
_COMPILED_NEGATIVE = _compile_weighted(NEGATIVE_PATTERNS)
_COMPILED_WATCHLIST = _compile(WATCHLIST_PATTERNS)


def score_item(item: PolicyItem) -> float:
    """Compute a relevance score for a single PolicyItem."""
    score = 0.0
    text = f"{item.title} {item.summary}"

    # 1. Source type bonus
    if item.source_type == "primary":
        score += 20.0
    else:
        score += 8.0

    # 2. Topic bonus from source catalogue tags
    for topic in item.topics:
        score += TOPIC_BONUS.get(topic, 0.0)

    # 3. Positive keyword matches
    for pattern, weight in _COMPILED_PRIORITY:
        if pattern.search(text):
            score += weight

    # 4. Negative keyword adjustments
    for pattern, weight in _COMPILED_NEGATIVE:
        if pattern.search(text):
            score += weight  # weight is negative

    # 5. Recency bonus
    if item.published:
        age = datetime.now(timezone.utc) - item.published.astimezone(timezone.utc)
        if age < timedelta(hours=24):
            score += 10.0
        elif age < timedelta(hours=48):
            score += 5.0

    # 6. Watchlist flag
    for pattern in _COMPILED_WATCHLIST:
        if pattern.search(text):
            item.is_watchlist = True
            break

    return max(0.0, min(score, 100.0))


def rank_items(items: list[PolicyItem]) -> list[PolicyItem]:
    """Score every item and return them sorted highest-first."""
    for item in items:
        item.score = score_item(item)

    ranked = sorted(items, key=lambda x: x.score, reverse=True)
    logger.info(
        "Ranked %d items; top score: %.1f",
        len(ranked),
        ranked[0].score if ranked else 0,
    )
    return ranked