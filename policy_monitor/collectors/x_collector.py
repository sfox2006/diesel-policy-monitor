"""
twitterapi.io collector for diesel and fuel policy signals.

The collector scans recent tweets from selected accounts and then applies the
local diesel/fuel/Hormuz/refinery keyword filter before adding matches to the
email briefing.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import requests

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)

ACCOUNT_TWEETS_URL = "https://api.twitterapi.io/twitter/user/last_tweets"


def _tweet_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return tweets from the response shapes twitterapi.io commonly emits."""
    candidates: list[Any] = [
        payload.get("tweets"),
        payload.get("data"),
        payload.get("result"),
        payload.get("results"),
    ]

    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend(
            [
                data.get("tweets"),
                data.get("data"),
                data.get("result"),
                data.get("results"),
            ]
        )

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]

    return []


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None

    for fmt in ("%a %b %d %H:%M:%S %z %Y",):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _tweet_id(tweet: dict[str, Any]) -> str:
    return str(
        tweet.get("id")
        or tweet.get("id_str")
        or tweet.get("tweetId")
        or tweet.get("tweet_id")
        or ""
    )


def _tweet_text(tweet: dict[str, Any]) -> str:
    text = tweet.get("text") or tweet.get("full_text") or tweet.get("tweetText") or ""
    return " ".join(str(text).split())


def _author(tweet: dict[str, Any], fallback_handle: str) -> tuple[str, str]:
    raw_author = tweet.get("author") or tweet.get("user") or {}
    if not isinstance(raw_author, dict):
        raw_author = {}

    username = (
        raw_author.get("userName")
        or raw_author.get("username")
        or raw_author.get("screen_name")
        or fallback_handle
    )
    username = str(username).lstrip("@") or fallback_handle
    name = str(raw_author.get("name") or username)
    return username, name


def _created_at(tweet: dict[str, Any]) -> datetime | None:
    return _parse_created_at(
        tweet.get("createdAt")
        or tweet.get("created_at")
        or tweet.get("created_at_iso")
        or tweet.get("time")
    )


def _tweet_url(tweet: dict[str, Any], username: str, tweet_id: str) -> str:
    url = tweet.get("url") or tweet.get("tweetUrl")
    if url:
        return str(url)
    if tweet_id:
        return f"https://x.com/{username}/status/{tweet_id}"
    return f"https://x.com/{username}"


def _metric(tweet: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = tweet.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def _metrics_summary(tweet: dict[str, Any]) -> str:
    likes = _metric(tweet, "likeCount", "like_count", "likes")
    reposts = _metric(tweet, "retweetCount", "retweet_count", "retweets", "reposts")
    replies = _metric(tweet, "replyCount", "reply_count", "replies")
    quotes = _metric(tweet, "quoteCount", "quote_count", "quotes")
    if not any((likes, reposts, replies, quotes)):
        return ""
    return f"Metrics: {likes} likes, {reposts} reposts, {replies} replies, {quotes} quotes."


def _matches_keywords(text: str) -> bool:
    haystack = text.lower()
    return any(term.lower() in haystack for term in config.X_KEYWORDS)


def _is_retweet(tweet: dict[str, Any], text: str) -> bool:
    tweet_type = str(tweet.get("type") or tweet.get("tweetType") or "").lower()
    return text.startswith("RT @") or tweet_type == "retweet" or bool(tweet.get("retweetedTweet"))


def _is_low_signal_tweet(text: str) -> bool:
    return bool(re.search(r"\blisten\b", text, flags=re.IGNORECASE))


def _to_item(tweet: dict[str, Any], fallback_handle: str) -> PolicyItem | None:
    tweet_id = _tweet_id(tweet)
    text = _tweet_text(tweet)
    if not text or not _matches_keywords(text):
        return None
    if _is_low_signal_tweet(text):
        return None
    if not config.X_INCLUDE_RETWEETS and _is_retweet(tweet, text):
        return None

    username, name = _author(tweet, fallback_handle)
    summary = f"@{username}: {text}"
    metric_text = _metrics_summary(tweet)
    if metric_text:
        summary = f"{summary} {metric_text}"

    return PolicyItem(
        title=f"@{username}: {text[:180]}",
        url=_tweet_url(tweet, username, tweet_id),
        source_name=f"X / {name} (@{username})",
        region="X",
        source_type="secondary",
        topics=["x_mentions", "reserves_and_prices", "supply_disruption"],
        published=_created_at(tweet),
        summary=summary,
    )


def collect_x_posts() -> list[PolicyItem]:
    """Collect recent matching tweets from configured twitterapi.io accounts."""
    if not config.TWITTERAPI_IO_KEY:
        logger.info("X collection skipped: TWITTERAPI_IO_KEY is not set")
        return []
    if not config.X_ACCOUNT_HANDLES:
        logger.info("X collection skipped: X_ACCOUNT_HANDLES is not set")
        return []

    headers = {"X-API-Key": config.TWITTERAPI_IO_KEY}
    items: list[PolicyItem] = []
    seen: set[str] = set()

    for handle in config.X_ACCOUNT_HANDLES:
        logger.info("Fetching recent tweets for @%s via twitterapi.io", handle)
        try:
            resp = requests.get(
                ACCOUNT_TWEETS_URL,
                headers=headers,
                params={"userName": handle},
                timeout=(10, config.REQUEST_TIMEOUT),
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("twitterapi.io fetch failed for @%s: %s", handle, exc)
            continue

        kept_for_account = 0
        for tweet in _tweet_records(resp.json()):
            item = _to_item(tweet, handle)
            if not item:
                continue

            key = _tweet_id(tweet) or item.url
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            kept_for_account += 1

            if kept_for_account >= config.X_MAX_RESULTS:
                break

    logger.info(
        "Collected %d matching X posts from %d account(s)",
        len(items),
        len(config.X_ACCOUNT_HANDLES),
    )
    return items
