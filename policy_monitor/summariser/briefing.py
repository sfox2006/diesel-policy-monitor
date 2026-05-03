"""
Briefing generator.

Takes ranked PolicyItems and produces:
  • output/email_summary.md   — the email body (Markdown)
  • output/full_briefing.md   — the full briefing with all items
  • output/items.json         — machine-readable dump
  • output/deep_dives/*.md    — one file per top-development item
"""

from __future__ import annotations

import json
import logging
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem
from policy_monitor.summariser.deep_dive import write_deep_dive

logger = logging.getLogger(__name__)


def _truncate(text: str, max_chars: int = 300) -> str:
    """Return text truncated to max_chars, ending on a word boundary."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" .,;:") + "…"


def _one_liner(item: PolicyItem) -> str:
    """Single-sentence summary: prefer existing summary, else title."""
    if item.summary:
        sentences = item.summary.split(". ")
        return sentences[0].strip().rstrip(".") + "."
    return item.title + "."


def generate_briefing(
    ranked_items: list[PolicyItem],
) -> tuple[Path, Path, Path]:
    """
    Generate all output artefacts.

    Returns (email_summary_path, full_briefing_path, items_json_path).
    """
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%d %B %Y")
    date_slug = today.strftime("%Y-%m-%d")

    top = ranked_items[: config.TOP_DEVELOPMENTS]
    watchlist = [i for i in ranked_items if i.is_watchlist][: config.WATCHLIST_ITEMS]
    statements = [i for i in ranked_items if i.is_statement and i not in top][:5]
    x_signals = [i for i in ranked_items if "x_mentions" in i.topics][: config.X_SECTION_ITEMS]
    tldr = ranked_items[: config.TLDR_BULLETS]

    # ── Deep dives for top items ──────────────────────────────────────────────
    logger.info("Generating deep dives for %d top items…", len(top))
    for item in top:
        try:
            path = write_deep_dive(item)
            item.deep_dive_path = str(path)
        except Exception as exc:
            logger.error("Deep dive failed for '%s': %s", item.title, exc)

    # ── Build email_summary.md ────────────────────────────────────────────────
    window_start = (today - timedelta(hours=config.MAX_ITEM_AGE_HOURS)).strftime("%H:%M UTC %d %b")
    window_end = today.strftime("%H:%M UTC %d %b")
    coverage_line = (
        f"*Coverage: {window_start} → {window_end} "
        f"· {len(ranked_items)} items · {len(top)} top developments · "
        f"primary & secondary sources across all monitored jurisdictions*"
    )

    email_lines: list[str] = [
        f"# Daily Diesel & Fuel Policy Briefing — {date_str}",
        "",
        coverage_line,
        "",
        "---",
        "",
        "## SECTION 1 — TL;DR",
        "",
    ]

    for item in tldr:
        flag = _region_flag(item.region)
        email_lines.append(f"- **[{item.region}]** {item.title}")
        email_lines.append(f"  → {_one_liner(item)}")
        email_lines.append("")

    email_lines += [
        "---",
        "",
        "## SECTION 2 — Top Developments",
        "",
    ]

    for i, item in enumerate(top, 1):
        email_lines.append(f"### {i}. {item.title}")
        email_lines.append("")

        # 2-3 sentence summary
        summary = item.summary or item.title
        summary = _truncate(summary, 600)
        # Ensure we have 2-3 sentences
        sentences = [s.strip() for s in summary.split(". ") if s.strip()]
        formatted = ". ".join(sentences[:3])
        if formatted and not formatted.endswith("."):
            formatted += "."
        email_lines.append(formatted)
        email_lines.append("")

        email_lines.append("**Why it matters:**")
        email_lines.append(_why_it_matters(item))
        email_lines.append("")

        email_lines.append("**Source links:**")
        email_lines.append(f"- Primary: [{item.source_name}]({item.url})")
        email_lines.append("")

        if item.deep_dive_path:
            email_lines.append(f"**Deep dive:** `{item.deep_dive_path}`")
        email_lines.append("")
        email_lines.append("---")
        email_lines.append("")

    # Section 3 — Watchlist
    email_lines += [
        "## SECTION 3 — Watchlist & Upcoming",
        "",
        "*Upcoming announcements, scheduled reports, policy reviews, trade meetings,*",
        "*and forward-looking signals relevant to Australian diesel fuel security.*",
        "",
    ]
    if watchlist:
        for item in watchlist:
            email_lines.append(f"- **[{item.region}]** {item.title}")
            email_lines.append(f"  → {_one_liner(item)}")
            email_lines.append(f"  Source: [{item.source_name}]({item.url})")
            email_lines.append("")
    else:
        email_lines.append(
            "_No upcoming announcements, scheduled reports, or regulatory deadlines flagged today._"
        )
        email_lines.append("")

    email_lines += [
        "---",
        "",
        "## SECTION 4 — Leader & Official Statements",
        "",
        "*Public statements on diesel, fuel security, reserves, imports or trade*",
        "*by PMs, presidents, premiers, energy ministers, finance ministers,*",
        "*trade ministers, transport ministers and relevant public agencies.*",
        "",
    ]
    if statements:
        for item in statements:
            email_lines.append(f"- **[{item.region}]** {item.title}")
            email_lines.append(f"  → {_one_liner(item)}")
            email_lines.append(f"  Source: [{item.source_name}]({item.url})")
            email_lines.append("")
    else:
        email_lines.append(
            "_No statements from tracked leaders or officials flagged today._"
        )
        email_lines.append("")

    email_lines += [
        "---",
        "",
        "## SECTION 5 — X Signals",
        "",
        "*Relevant posts from configured X searches/accounts mentioning diesel,*",
        "*petrol, refineries, fuel security, Hormuz, or related supply risks.*",
        "",
    ]
    if x_signals:
        for item in x_signals:
            email_lines.append(f"- **{item.source_name}**")
            email_lines.append(f"  → {_one_liner(item)}")
            email_lines.append(f"  Link: [{item.url}]({item.url})")
            email_lines.append("")
    else:
        email_lines.append("_No relevant X posts flagged today._")
        email_lines.append("")

    email_lines += [
        "---",
        "",
        f"*Briefing generated {today.strftime('%Y-%m-%d %H:%M UTC')} by PolicyMonitor.*",
        f"*Full briefing attached as `full_briefing_{date_slug}.md`.*",
        "",
        f"*Delivered to sam.fox@mandalapartners.com · PolicyMonitor · Mandala Partners Intelligence*",
    ]

    email_md = "\n".join(email_lines)

    # ── Build full_briefing.md ────────────────────────────────────────────────
    full_lines: list[str] = [
        f"# Full Diesel & Fuel Policy Briefing — {date_str}",
        f"*{len(ranked_items)} items collected and ranked*",
        "",
        "---",
        "",
    ]

    for rank, item in enumerate(ranked_items, 1):
        pub = item.published.strftime("%d %b %Y") if item.published else "unknown date"
        full_lines.append(
            f"## {rank}. [{item.source_type.upper()}] {item.title}"
        )
        full_lines.append(
            f"**Source:** {item.source_name} | **Region:** {item.region} | "
            f"**Score:** {item.score:.1f} | **Published:** {pub}"
        )
        full_lines.append(f"**Topics:** {', '.join(item.topics)}")
        full_lines.append(f"**URL:** {item.url}")
        if item.summary:
            full_lines.append("")
            full_lines.append(item.summary)
        if item.deep_dive_path:
            full_lines.append(f"**Deep dive:** `{item.deep_dive_path}`")
        full_lines.append("")
        full_lines.append("---")
        full_lines.append("")

    full_md = "\n".join(full_lines)

    # ── Write files ───────────────────────────────────────────────────────────
    email_path = config.OUTPUT_DIR / "email_summary.md"
    full_path = config.OUTPUT_DIR / "full_briefing.md"
    json_path = config.OUTPUT_DIR / "items.json"

    email_path.write_text(email_md, encoding="utf-8")
    full_path.write_text(full_md, encoding="utf-8")
    json_path.write_text(
        json.dumps([i.to_dict() for i in ranked_items], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(
        "Briefing written: email_summary.md (%d chars), full_briefing.md (%d chars), items.json",
        len(email_md), len(full_md),
    )
    return email_path, full_path, json_path


def _why_it_matters(item: PolicyItem) -> str:
    """Generate a short 'why it matters' sentence from topic tags."""
    topic_phrases: dict[str, str] = {
        "reserves_and_prices": "Australian diesel reserve levels and wholesale prices directly determine the nation's ability to meet its IEA 90-day stockholding obligation and sustain critical supply chains",
        "shipments": "tanker arrivals and import volumes at Australian terminals are the primary indicator of near-term diesel availability and reserve trajectory",
        "partner_country": "actions by Australia's key diesel supply partners — Japan, Malaysia, Singapore, South Korea and Thailand — directly affect what volume and at what price Australia can secure fuel imports",
        "supply_disruption": "disruptions to refining capacity or shipping routes feeding Australia's import terminals can rapidly erode reserve buffers and push wholesale prices higher",
        "policy_and_legislation": "ministerial statements and legislative action shape Australia's fuel security framework, IEA compliance posture, and the regulatory environment for fuel importers and retailers",
    }
    for topic in item.topics:
        phrase = topic_phrases.get(topic)
        if phrase:
            return f"This development matters because {phrase}."
    return "This development warrants monitoring for downstream implications on Australian fuel security."


def _region_flag(region: str) -> str:
    flags = {
        "Australia": "🇦🇺",
        "Japan": "🇯🇵",
        "Malaysia": "🇲🇾",
        "Singapore": "🇸🇬",
        "SouthKorea": "🇰🇷",
        "Thailand": "🇹🇭",
        "International": "🌐",
        "Americas": "🌎",
        "Europe": "🇪🇺",
        "Asia": "🌏",
        "AsiaPacific": "🌏",
        "Gulf": "🌍",
        "Global": "🌐",
    }
    return flags.get(region, "")
