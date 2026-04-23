"""
Collector runner — iterates all sources, dispatches to rss or html collector,
applies a 24-hour age filter, and returns a flat deduplicated list of PolicyItems.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from policy_monitor import config
from policy_monitor.collectors.html_collector import collect_html
from policy_monitor.collectors.models import PolicyItem
from policy_monitor.collectors.rss_collector import collect_rss
from policy_monitor.collectors.sources import SOURCES

logger = logging.getLogger(__name__)


def _within_window(item: PolicyItem, cutoff: datetime) -> bool:
    """
    Return True if the item should be included.

    Rules:
    - If the item has a publish date and it's older than the cutoff → exclude.
    - If the item has no publish date (HTML-scraped) → include (age unknown).
    """
    if item.published is None:
        return True
    return item.published.astimezone(timezone.utc) >= cutoff


def run_all_collectors() -> list[PolicyItem]:
    """
    Iterate every source in the catalogue.
    Prefer RSS; fall back to HTML scraping if no feed is defined.
    Drops items older than MAX_ITEM_AGE_HOURS (default: 24h).
    Returns a deduplicated-by-URL list of PolicyItems.
    """
    cutoff: datetime | None = None
    if config.MAX_ITEM_AGE_HOURS > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.MAX_ITEM_AGE_HOURS)
        logger.info(
            "Age filter: keeping items published after %s",
            cutoff.strftime("%Y-%m-%d %H:%M UTC"),
        )

    all_items: list[PolicyItem] = []
    seen_urls: set[str] = set()
    dropped_age = 0

    for source in SOURCES:
        try:
            if source.get("feed"):
                items = collect_rss(source)
            elif source.get("scrape_url"):
                items = collect_html(source)
            else:
                logger.warning("Source has no feed or scrape_url: %s", source["name"])
                continue
        except Exception as exc:
            logger.error("Unexpected error collecting %s: %s", source["name"], exc, exc_info=True)
            continue

        for item in items:
            if not item.url or item.url in seen_urls:
                continue
            if cutoff and not _within_window(item, cutoff):
                dropped_age += 1
                continue
            seen_urls.add(item.url)
            all_items.append(item)

    logger.info(
        "Collected %d unique items from %d sources (%d dropped: older than %dh)",
        len(all_items), len(SOURCES), dropped_age, config.MAX_ITEM_AGE_HOURS,
    )
    return all_items
