"""
RSS / Atom feed collector.
Uses feedparser to pull items from every source that has a `feed` URL.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import feedparser
import requests

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
                "Accept": "application/rss+xml, application/atom+xml, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
    return _SESSION


def _parse_date(entry: feedparser.util.FeedParserDict) -> datetime | None:
    """Return a timezone-aware datetime from the best available date field."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def collect_rss(source: Source) -> list[PolicyItem]:
    """Fetch and parse a single RSS/Atom feed, return PolicyItems."""
    feed_url: str = source.get("feed", "")
    if not feed_url:
        return []

    logger.info("RSS  ← %s  (%s)", source["name"], feed_url)

    try:
        resp = _session().get(feed_url, timeout=(10, config.REQUEST_TIMEOUT))
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except requests.RequestException as exc:
        logger.error("RSS fetch failed for %s: %s", source["name"], exc)
        return []
    except Exception as exc:
        logger.error("RSS parse failed for %s: %s", source["name"], exc)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Malformed feed for %s: %s", source["name"], feed.bozo_exception)
        return []

    items: list[PolicyItem] = []
    for entry in feed.entries:
        title: str = getattr(entry, "title", "").strip()
        url: str = getattr(entry, "link", "").strip()
        if not title or not url:
            continue

        # Summary: prefer 'summary', fallback to 'content'
        summary = getattr(entry, "summary", "")
        if not summary and hasattr(entry, "content"):
            summary = entry.content[0].value if entry.content else ""

        # Strip HTML from summary
        summary = _strip_html(summary)[:600]

        item = PolicyItem(
            title=title,
            url=url,
            source_name=source["name"],
            region=source.get("region", "Global"),
            source_type=source.get("type", "secondary"),
            topics=list(source.get("topics", [])),
            published=_parse_date(entry),
            summary=summary,
        )
        items.append(item)

    logger.debug("  → %d items from %s", len(items), source["name"])
    time.sleep(config.REQUEST_DELAY)
    return items


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string using basic parsing."""
    from html.parser import HTMLParser

    class _Stripper(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    s = _Stripper()
    s.feed(text)
    return " ".join(s.parts).strip()
