"""
Deep-dive generator.

For each top item, attempts to fetch the full source page and extract a longer
body of text, then writes a structured Markdown file in output/deep_dives/.

No external LLM is used — the deep-dive is structured from the scraped body
text plus structured metadata. If you later add an LLM step, plug it in here.
"""

from __future__ import annotations

import logging
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)

_IMPLICATION_HINTS: dict[str, list[str]] = {
    "reserves_and_prices": [
        "Trajectory of Australia's IEA 90-day stockholding compliance",
        "Pressure on wholesale and terminal gate diesel prices for transport and agriculture",
        "Risk of station outages in regional and remote areas if reserves fall further",
    ],
    "shipments": [
        "Near-term availability of diesel at Australian import terminals (Botany, Geelong, Fremantle, Brisbane)",
        "Lead time implications — tanker bookings typically 4-6 weeks ahead of delivery",
        "Potential arbitrage opportunities or shortfalls if shipment volumes diverge from trend",
    ],
    "partner_country": [
        "Impact on volumes Australia can secure from this supply partner",
        "Price effects if the partner redirects exports or draws down shared refinery capacity",
        "Diplomatic and trade implications for Australia's bilateral fuel security arrangements",
    ],
    "supply_disruption": [
        "Immediate risk to import volumes if the disruption affects key shipping routes or refineries",
        "Potential activation of IEA collective action mechanisms",
        "Downstream effects on transport, agriculture, mining and defence fuel supply",
    ],
    "policy_and_legislation": [
        "Changes to Australia's minimum stockholding obligation framework",
        "Regulatory obligations for fuel importers, wholesalers and retailers",
        "Budget and appropriations implications for government fuel security spending",
    ],
}


def _fetch_body(url: str) -> str:
    """Fetch a webpage and return its main body text (best-effort)."""
    try:
        resp = requests.get(
            url,
            timeout=config.REQUEST_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove boilerplate
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Try common content selectors
        for selector in ("article", "main", ".content", "#content", ".post-body"):
            el = soup.select_one(selector)
            if el:
                return el.get_text(" ", strip=True)[:3000]

        return soup.get_text(" ", strip=True)[:3000]
    except Exception as exc:
        logger.warning("Could not fetch body for deep dive (%s): %s", url, exc)
        return ""


def _implications(topics: list[str]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for topic in topics:
        for bullet in _IMPLICATION_HINTS.get(topic, []):
            if bullet not in seen:
                lines.append(f"- {bullet}")
                seen.add(bullet)
    if not lines:
        lines = [
            "- Monitor downstream investment and procurement patterns",
            "- Assess regulatory compliance requirements in affected jurisdictions",
        ]
    return "\n".join(lines)


def write_deep_dive(item: PolicyItem, body: str | None = None) -> Path:
    """
    Write a Markdown deep-dive file for a PolicyItem.
    Returns the path to the created file.
    """
    if body is None:
        body = _fetch_body(item.url)

    date_str = (
        item.published.strftime("%d %B %Y")
        if item.published
        else datetime.now(timezone.utc).strftime("%d %B %Y")
    )

    # Wrap body text for readability
    body_wrapped = textwrap.fill(body, width=100) if body else "_Body text not available._"

    content = f"""\
# Deep Dive: {item.title}

**Source:** {item.source_name}
**Region:** {item.region}
**Date:** {date_str}
**Topics:** {", ".join(item.topics)}
**URL:** {item.url}
**Relevance score:** {item.score:.1f}

---

## Summary

{item.summary or "_No summary extracted._"}

---

## Full Text (extracted)

{body_wrapped}

---

## Policy Context

This item relates to the following policy domains: **{", ".join(item.topics)}**.

It originates from a **{item.source_type}** source in the **{item.region}** region,
indicating {"a direct governmental or regulatory action" if item.source_type == "primary"
           else "secondary reporting on a policy development"}.

---

## Potential Implications

### Fuel Reserves & Pricing
{_implications(["reserves_and_prices"])}

### Supply Chain & Shipments
{_implications(["shipments", "supply_disruption"])}

### Trading Partner & Diplomatic
{_implications(["partner_country"])}

### Policy & Legislation
{_implications(["policy_and_legislation"])}

---

*Generated by PolicyMonitor on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}*
"""

    slug = item.slug
    path = config.DEEP_DIVES_DIR / f"{slug}.md"

    # Avoid slug collisions
    counter = 1
    while path.exists():
        path = config.DEEP_DIVES_DIR / f"{slug}-{counter}.md"
        counter += 1

    path.write_text(content, encoding="utf-8")
    logger.debug("Deep dive written: %s", path)
    return path