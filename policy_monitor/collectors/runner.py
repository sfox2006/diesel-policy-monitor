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
from policy_monitor.collectors.sources import SOURCES, Source
from policy_monitor.collectors.x_collector import collect_x_posts

logger = logging.getLogger(__name__)


_BROAD_LEGACY_SOURCE_KEYWORDS = (
    "Services Union",
    "United Workers Union",
    "Shop, Distributive and Allied Employees",
    "Australian Industry Group",
    "Business Council of Australia",
    "Australian Chamber of Commerce",
    "Australian Retailers Association",
    "Mining and Energy Union",
    "Australian Workers Union",
    "Minerals Council of Australia",
    "Chamber of Minerals and Energy",
    "National Farmers Federation",
    "GrainGrowers",
    "Meat and Livestock Australia",
    "Dairy Australia",
    "Cotton Australia",
    "Master Builders Australia",
    "Housing Industry Association",
    "Australian Constructors Association",
    "Transport Workers Union",
    "Maritime Union of Australia",
    "Australian Trucking Association",
    "Australian Logistics Council",
    "Shipping Australia",
    "Energy Networks Australia",
    "Australian Pipelines and Gas Association",
    "Clean Energy Council",
    "Institute of Public Administration Australia",
    "Australian Manufacturing Workers Union",
    "RenewEconomy",
)


def _active_sources() -> list[Source]:
    """Return the source list for the configured crawl profile."""
    if config.SOURCE_PROFILE == "all":
        return SOURCES

    active = [
        source
        for source in SOURCES
        if not any(keyword in source["name"] for keyword in _BROAD_LEGACY_SOURCE_KEYWORDS)
    ]
    skipped = len(SOURCES) - len(active)
    logger.info(
        "Source profile '%s': using %d sources (%d broad legacy sources skipped)",
        config.SOURCE_PROFILE,
        len(active),
        skipped,
    )
    return active


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

    x_items = collect_x_posts()
    for item in x_items:
        if not item.url or item.url in seen_urls:
            continue
        if cutoff and not _within_window(item, cutoff):
            dropped_age += 1
            continue
        seen_urls.add(item.url)
        all_items.append(item)

    sources = _active_sources()
    total_sources = len(sources)
    for index, source in enumerate(sources, start=1):
        logger.info("Collecting source %d/%d: %s", index, total_sources, source["name"])
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

        logger.info("Source %d/%d returned %d items: %s", index, total_sources, len(items), source["name"])

        for item in items:
            if not item.url or item.url in seen_urls:
                continue
            if cutoff and not _within_window(item, cutoff):
                dropped_age += 1
                continue
            seen_urls.add(item.url)
            all_items.append(item)

    logger.info(
        "Collected %d unique items from %d sources plus X (%d dropped: older than %dh)",
        len(all_items), total_sources, dropped_age, config.MAX_ITEM_AGE_HOURS,
    )
    return all_items
