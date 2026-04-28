"""
HTML scraping fallback collector.
Used for sources that don't provide RSS feeds.
Uses requests + BeautifulSoup with per-source CSS-selector config.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem
from policy_monitor.collectors.sources import Source

logger = logging.getLogger(__name__)

_SESSION: requests.Session | None = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(
            {
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
    return _SESSION


def collect_html(source: Source) -> list[PolicyItem]:
    """Scrape an HTML page for policy items using per-source selectors."""
    url: str = source.get("scrape_url", "")
    if not url:
        return []

    cfg: dict = source.get("scrape_cfg", {})
    list_selector: str = cfg.get("list_selector", "")
    title_selector: str = cfg.get("title", "a")
    link_selector: str = cfg.get("link", "a")

    if not list_selector:
        logger.warning("No list_selector for %s — skipping HTML scrape", source["name"])
        return []

    logger.info("HTML ← %s  (%s)", source["name"], url)

    try:
        # Two-part timeout: (connect_timeout, read_timeout)
        # Prevents hanging indefinitely when a server connects but stalls sending data
        resp = _session().get(url, timeout=(10, config.REQUEST_TIMEOUT))
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("HTML fetch failed for %s: %s", source["name"], exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    rows = soup.select(list_selector)

    items: list[PolicyItem] = []
    for row in rows[:50]:  # cap to avoid runaway pages
        title, href = _extract_title_href(row, title_selector, link_selector, url)
        if not title or not href:
            continue

        summary = _extract_summary(row, title)

        item = PolicyItem(
            title=title,
            url=href,
            source_name=source["name"],
            region=source.get("region", "Global"),
            source_type=source.get("type", "secondary"),
            topics=list(source.get("topics", [])),
            published=None,   # HTML pages rarely expose structured dates
            summary=summary,
        )
        items.append(item)

    logger.debug("  → %d items from %s", len(items), source["name"])
    time.sleep(config.REQUEST_DELAY)
    return items


def _extract_title_href(
    row: Tag,
    title_sel: str,
    link_sel: str,
    base_url: str,
) -> tuple[str, str]:
    """Extract (title_text, absolute_href) from a BeautifulSoup tag."""
    # Title
    title_tag = row.select_one(title_sel)
    if title_tag is None:
        return "", ""
    title = title_tag.get_text(strip=True)

    # Link
    link_tag = row.select_one(link_sel)
    href = ""
    if link_tag and link_tag.name == "a":
        href = link_tag.get("href", "")
    elif row.name == "a":
        href = row.get("href", "")

    if href:
        href = urljoin(base_url, href)

    return title, href


def _extract_summary(row: Tag, title: str) -> str:
    """Extract a short listing snippet from a scraped row."""
    text = row.get_text(" ", strip=True)
    if not text:
        return ""
    if text.startswith(title):
        text = text[len(title):].strip(" -–—|")
    return " ".join(text.split())[:600]
