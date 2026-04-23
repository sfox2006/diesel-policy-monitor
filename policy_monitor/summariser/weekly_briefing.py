"""
Weekly outlook briefing generator.

Runs every 7 days (on the configured WEEKLY_DAY_OF_WEEK).
Collects from all sources with a 168-hour (7-day) window, ranks,
and produces:

  output/weekly_summary.md      — email body
  output/weekly_full.md         — full ranked list
  output/weekly_YYYY-MM-DD.md   — dated archive copy

Email structure
───────────────
  SECTION 1 — Week in Review   (top 10 developments, past 7 days)
  SECTION 2 — Regional Roundup (one headline per region)
  SECTION 3 — Week Ahead       (upcoming votes, deadlines, consultations)
  SECTION 4 — Trend Watch      (recurring themes across the week)
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem
from policy_monitor.collectors.runner import run_all_collectors
from policy_monitor.dedupe.store import DedupeStore
from policy_monitor.ranking.scorer import rank_items

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

WEEK_HOURS = 168   # 7 days

TOP_WEEKLY_DEVELOPMENTS = 10
REGIONAL_ROUNDUP_REGIONS = ["Americas", "Europe", "Asia", "AsiaPacific", "Gulf"]

# Forward-looking phrases that signal "Week Ahead" items
AHEAD_PATTERNS = [
    r"\bexpected to (vote|pass|publish|release|announc|decide)",
    r"\bupcoming (vote|hearing|deadline|consultation|review|summit)",
    r"\bdue (to|by|on) (the )?(end of the week|monday|tuesday|wednesday|thursday|friday|next week)",
    r"\bscheduled (for|to)",
    r"\bwill (vote|decide|release|announc|publish)",
    r"\bclosing date|comment period (closes|ends|due)",
    r"\bsecond reading|third reading|royal assent",
    r"\bcommittee hearing|parliamentary question",
    r"\bG7|G20|APEC|COP\d+|UN General Assembly",
]
_AHEAD_RE = [re.compile(p, re.IGNORECASE) for p in AHEAD_PATTERNS]

# Topic → plain-English label for trend watch
TOPIC_LABELS: dict[str, str] = {
    "export_controls":      "Export controls & technology restrictions",
    "critical_minerals":    "Critical minerals & mining",
    "industrial_policy":    "Industrial policy & manufacturing strategy",
    "subsidies":            "Subsidies & industrial finance",
    "sovereign_investment": "Sovereign investment & development finance",
    "ai_infrastructure":    "AI infrastructure & semiconductor policy",
    "supply_chains":        "Supply chain restructuring",
    "energy":               "Energy transition policy",
    "trade":                "Trade policy & market access",
    "mining":               "Mining investment",
    "legislation":          "New legislation & regulation",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _one_liner(item: PolicyItem) -> str:
    if item.summary:
        return item.summary.split(". ")[0].strip().rstrip(".") + "."
    return item.title + "."


def _is_ahead(item: PolicyItem) -> bool:
    text = f"{item.title} {item.summary}"
    return any(p.search(text) for p in _AHEAD_RE)


def _top_topics(items: list[PolicyItem], n: int = 5) -> list[tuple[str, int]]:
    counts: Counter = Counter()
    for item in items:
        for t in item.topics:
            counts[t] += 1
    return counts.most_common(n)


def _trend_commentary(topic: str, count: int, total: int) -> str:
    label = TOPIC_LABELS.get(topic, topic.replace("_", " ").title())
    pct = int(count / total * 100) if total else 0
    if pct >= 30:
        intensity = "dominated"
    elif pct >= 20:
        intensity = "featured heavily in"
    else:
        intensity = "appeared across"
    return f"**{label}** {intensity} this week's coverage ({count} items, {pct}% of developments)."


def _region_best(items: list[PolicyItem], region: str) -> PolicyItem | None:
    regional = [i for i in items if i.region == region]
    return regional[0] if regional else None


# ── Main generator ────────────────────────────────────────────────────────────

def generate_weekly_briefing() -> tuple[Path, Path]:
    """
    Collect 7 days of policy items, rank them, and write the weekly briefing.
    Returns (email_summary_path, full_briefing_path).
    """
    today = datetime.now(timezone.utc)
    week_start = today - timedelta(hours=WEEK_HOURS)
    date_str = today.strftime("%d %B %Y")
    week_range = f"{week_start.strftime('%d %b')} – {today.strftime('%d %b %Y')}"

    logger.info("Generating weekly briefing for %s", week_range)

    # ── Collect with 7-day window (temporarily override age config) ───────────
    original_age = config.MAX_ITEM_AGE_HOURS
    config.MAX_ITEM_AGE_HOURS = WEEK_HOURS  # type: ignore[assignment]
    try:
        raw_items = run_all_collectors()
    finally:
        config.MAX_ITEM_AGE_HOURS = original_age  # type: ignore[assignment]

    if not raw_items:
        logger.warning("No items collected for weekly briefing.")
        # Still write an empty briefing
        raw_items = []

    # Dedupe — use a separate pass so weekly doesn't poison daily dedupe window
    store = DedupeStore()
    try:
        # For the weekly we want ALL items from the past 7 days, even ones
        # that appeared in daily briefings, so we skip the 20h filter and
        # just do URL-level dedup within this run.
        seen: set[str] = set()
        unique: list[PolicyItem] = []
        for item in raw_items:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
    finally:
        store.close()

    ranked = rank_items(unique) if unique else []
    total = len(ranked)

    top10 = ranked[:TOP_WEEKLY_DEVELOPMENTS]
    ahead_items = [i for i in ranked if _is_ahead(i)][:5]
    top_topics = _top_topics(ranked, n=5)

    # ── Build email_summary.md ────────────────────────────────────────────────
    lines: list[str] = [
        f"# Weekly Industrial Policy Outlook — {week_range}",
        "",
        f"*{total} developments monitored across {len(REGIONAL_ROUNDUP_REGIONS)} regions · "
        f"primary and secondary sources · generated {today.strftime('%d %b %Y %H:%M UTC')}*",
        "",
        "---",
        "",
        "## SECTION 1 — WEEK IN REVIEW",
        f"*Top {min(TOP_WEEKLY_DEVELOPMENTS, total)} developments of the past 7 days, ranked by policy significance*",
        "",
    ]

    for i, item in enumerate(top10, 1):
        pub = item.published.strftime("%d %b") if item.published else "this week"
        lines.append(f"### {i}. {item.title}")
        lines.append(f"*{item.source_name} · {item.region} · {pub} · score {item.score:.0f}*")
        lines.append("")
        summary = item.summary or item.title
        sentences = [s.strip() for s in summary.split(". ") if s.strip()]
        lines.append(". ".join(sentences[:3]).rstrip(".") + ".")
        lines.append("")
        lines.append(f"→ [Source]({item.url})")
        lines.append("")

    lines += [
        "---",
        "",
        "## SECTION 2 — REGIONAL ROUNDUP",
        "*One key development per region this week*",
        "",
    ]

    for region in REGIONAL_ROUNDUP_REGIONS:
        best = _region_best(ranked, region)
        if best:
            lines.append(f"**{region}** — {best.title}")
            lines.append(f"→ {_one_liner(best)}  [{best.source_name}]({best.url})")
        else:
            lines.append(f"**{region}** — No significant developments flagged this week.")
        lines.append("")

    lines += [
        "---",
        "",
        "## SECTION 3 — WEEK AHEAD: THINGS TO WATCH",
        "*Upcoming votes, deadlines, hearings, and consultations*",
        "",
    ]

    if ahead_items:
        for item in ahead_items:
            lines.append(f"- **{item.title}**")
            lines.append(f"  → {_one_liner(item)}  [{item.source_name}]({item.url})")
            lines.append("")
    else:
        lines.append(
            "_No specific upcoming deadlines or votes flagged in this week's sources. "
            "Monitor parliamentary calendars and regulatory dockets in key jurisdictions._"
        )
        lines.append("")

    # Generic standing watchlist based on the week's dominant topics
    if top_topics:
        lines.append("**Standing watch items based on this week's trend:**")
        lines.append("")
        for topic, count in top_topics[:3]:
            label = TOPIC_LABELS.get(topic, topic.replace("_", " ").title())
            lines.append(f"- **{label}**: Active this week ({count} items). Monitor for follow-on regulatory action.")
        lines.append("")

    lines += [
        "---",
        "",
        "## SECTION 4 — TREND WATCH",
        "*Recurring themes across this week's 241-source coverage*",
        "",
    ]

    if top_topics:
        for topic, count in top_topics:
            lines.append(f"- {_trend_commentary(topic, count, total)}")
        lines.append("")
    else:
        lines.append("_Insufficient data for trend analysis this week._")
        lines.append("")

    # Structural observations
    primary_count = sum(1 for i in ranked if i.source_type == "primary")
    secondary_count = total - primary_count
    if total:
        lines.append(
            f"**Source mix:** {primary_count} primary sources ({int(primary_count/total*100)}%) "
            f"· {secondary_count} secondary sources ({int(secondary_count/total*100)}%). "
            f"{'High primary weighting — direct government signals dominate this week.' if primary_count > secondary_count else 'Secondary sources leading — watch for primary confirmation of reported policy signals.'}"
        )
        lines.append("")

    lines += [
        "---",
        "",
        f"*Weekly Industrial Policy Outlook generated by PolicyMonitor · "
        f"{today.strftime('%Y-%m-%d %H:%M UTC')}*",
        f"*Full ranked list of {total} developments attached.*",
    ]

    email_md = "\n".join(lines)

    # ── Build full weekly ─────────────────────────────────────────────────────
    full_lines: list[str] = [
        f"# Full Weekly Policy Developments — {week_range}",
        f"*{total} items · ranked by policy significance*",
        "",
        "---",
        "",
    ]
    for rank, item in enumerate(ranked, 1):
        pub = item.published.strftime("%d %b %Y") if item.published else "unknown"
        full_lines.append(f"## {rank}. [{item.source_type.upper()}] {item.title}")
        full_lines.append(
            f"**Source:** {item.source_name} | **Region:** {item.region} | "
            f"**Score:** {item.score:.1f} | **Published:** {pub}"
        )
        full_lines.append(f"**Topics:** {', '.join(item.topics)}")
        full_lines.append(f"**URL:** {item.url}")
        if item.summary:
            full_lines.append("")
            full_lines.append(item.summary)
        full_lines += ["", "---", ""]

    full_md = "\n".join(full_lines)

    # ── Write output files ────────────────────────────────────────────────────
    email_path = config.OUTPUT_DIR / "weekly_summary.md"
    full_path = config.OUTPUT_DIR / "weekly_full.md"
    archive_path = config.OUTPUT_DIR / f"weekly_{today.strftime('%Y-%m-%d')}.md"

    email_path.write_text(email_md, encoding="utf-8")
    full_path.write_text(full_md, encoding="utf-8")
    archive_path.write_text(email_md, encoding="utf-8")

    logger.info(
        "Weekly briefing written: %s (%d chars) | archive: %s",
        email_path, len(email_md), archive_path,
    )
    return email_path, full_path
