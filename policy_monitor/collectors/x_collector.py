"""
X API v2 collector for diesel and fuel policy signals.

Uses Recent Search when X_BEARER_TOKEN is configured. Search terms can be
supplied directly with X_SEARCH_QUERIES, or generated for specific accounts
with X_ACCOUNT_HANDLES.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)

RECENT_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"

DEFAULT_X_TERMS = (
    "diesel OR petrol OR gasoline OR gasoil OR fuel OR refinery OR refineries "
    'OR "fuel security" OR "Strait of Hormuz" OR Hormuz OR "fuel reserve" '
    'OR "petroleum reserve" OR "fuel shortage"'
)


def _base_query() -> str:
    query = f"({DEFAULT_X_TERMS}) lang:en"
    if not config.X_INCLUDE_RETWEETS:
        query += " -is:retweet"
    return query


def _account_queries() -> list[str]:
    if not config.X_ACCOUNT_HANDLES:
        return []

    accounts = [f"from:{handle}" for handle in config.X_ACCOUNT_HANDLES]
    # Keep query length conservative for the Recent Search endpoint.
    chunks: list[list[str]] = []
    current: list[str] = []
    for account in accounts:
        candidate = current + [account]
        if len(" OR ".join(candidate)) > 220:
            chunks.append(current)
            current = [account]
        else:
            current = candidate
    if current:
        chunks.append(current)

    return [f"{_base_query()} ({' OR '.join(chunk)})" for chunk in chunks if chunk]


def _queries() -> list[str]:
    queries = list(config.X_SEARCH_QUERIES) or [_base_query()]
    queries.extend(_account_queries())
    return list(dict.fromkeys(queries))


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _author_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    users = payload.get("includes", {}).get("users", [])
    return {user["id"]: user for user in users if user.get("id")}


def _metrics_summary(metrics: dict[str, Any]) -> str:
    if not metrics:
        return ""
    return (
        "Metrics: "
        f"{metrics.get('like_count', 0)} likes, "
        f"{metrics.get('retweet_count', 0)} reposts, "
        f"{metrics.get('reply_count', 0)} replies, "
        f"{metrics.get('quote_count', 0)} quotes."
    )


def _tweet_url(author: dict[str, Any] | None, tweet_id: str) -> str:
    username = (author or {}).get("username")
    if username:
        return f"https://x.com/{username}/status/{tweet_id}"
    return f"https://x.com/i/web/status/{tweet_id}"


def _to_item(tweet: dict[str, Any], author: dict[str, Any] | None) -> PolicyItem | None:
    tweet_id = tweet.get("id")
    text = " ".join((tweet.get("text") or "").split())
    if not tweet_id or not text:
        return None

    username = (author or {}).get("username", "unknown")
    name = (author or {}).get("name", username)
    metrics = tweet.get("public_metrics", {})
    summary = f"@{username}: {text}"
    metric_text = _metrics_summary(metrics)
    if metric_text:
        summary = f"{summary} {metric_text}"

    return PolicyItem(
        title=f"@{username}: {text[:180]}",
        url=_tweet_url(author, tweet_id),
        source_name=f"X / {name} (@{username})",
        region="X",
        source_type="secondary",
        topics=["x_mentions", "reserves_and_prices", "supply_disruption"],
        published=_parse_created_at(tweet.get("created_at")),
        summary=summary,
    )


def collect_x_posts() -> list[PolicyItem]:
    """Collect recent X posts for configured fuel-policy queries."""
    if not config.X_BEARER_TOKEN:
        logger.info("X collection skipped: X_BEARER_TOKEN is not set")
        return []

    start_time = datetime.now(timezone.utc) - timedelta(hours=config.X_LOOKBACK_HOURS)
    headers = {"Authorization": f"Bearer {config.X_BEARER_TOKEN}"}
    params_base = {
        "max_results": config.X_MAX_RESULTS,
        "tweet.fields": "created_at,author_id,public_metrics,referenced_tweets",
        "expansions": "author_id",
        "user.fields": "name,username,verified,public_metrics",
        "start_time": start_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }

    items: list[PolicyItem] = []
    seen_ids: set[str] = set()

    for query in _queries():
        logger.info("X search: %s", query)
        try:
            resp = requests.get(
                RECENT_SEARCH_URL,
                headers=headers,
                params={**params_base, "query": query},
                timeout=(10, config.REQUEST_TIMEOUT),
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("X search failed: %s", exc)
            continue

        payload = resp.json()
        authors = _author_lookup(payload)
        for tweet in payload.get("data", []):
            tweet_id = tweet.get("id")
            if not tweet_id or tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)
            item = _to_item(tweet, authors.get(tweet.get("author_id")))
            if item:
                items.append(item)

    logger.info("Collected %d X posts from %d query/queries", len(items), len(_queries()))
    return items
