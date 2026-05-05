"""
twitterapi.io collector for diesel and fuel policy signals.

The collector scans recent tweets from selected accounts and then applies the
local diesel/fuel/Hormuz/refinery keyword filter before adding matches to the
email briefing.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)

ACCOUNT_TWEETS_URL = "https://api.twitterapi.io/twitter/user/last_tweets"

PODCAST_DOMAINS = (
    "spotify.com",
    "open.spotify.com",
    "podcasts.apple.com",
    "music.apple.com",
    "apple.co",
    "soundcloud.com",
    "audioboom.com",
    "podbean.com",
    "libsyn.com",
    "anchor.fm",
    "megaphone.fm",
    "omny.fm",
    "acast.com",
    "buzzsprout.com",
    "iheart.com",
)

PODCAST_PHRASES = (
    r"\blisten now\b",
    r"\blisten to (our|the|this|latest|new)\b",
    r"\bnew episode\b",
    r"\blatest episode\b",
    r"\bpodcast\b",
    r"\bepisode out\b",
    r"\bstream now\b",
    r"\bsubscribe\b",
    r"#podcast\b",
    r"#podcasts\b",
    r"#newepisode\b",
)


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
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
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


def _tweet_urls(tweet: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("url", "tweetUrl"):
        value = tweet.get(key)
        if value:
            urls.append(str(value))

    entities = tweet.get("entities")
    if isinstance(entities, dict):
        for raw_url in entities.get("urls", []):
            if not isinstance(raw_url, dict):
                continue
            for key in ("expanded_url", "expandedUrl", "display_url", "url"):
                value = raw_url.get(key)
                if value:
                    urls.append(str(value))

    return urls


def _is_low_signal_tweet(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in PODCAST_PHRASES)


def _is_low_signal_tweet_record(tweet: dict[str, Any], text: str) -> bool:
    if _is_low_signal_tweet(text):
        return True
    url_text = " ".join(_tweet_urls(tweet)).lower()
    return any(domain in url_text for domain in PODCAST_DOMAINS)


def _scan_limit_for_handle(handle: str) -> int:
    handle_key = handle.strip().lstrip("@").lower()
    person_handles = {h.lower() for h in config.X_PERSON_ACCOUNT_HANDLES}
    media_handles = {h.lower() for h in config.X_MEDIA_ACCOUNT_HANDLES}
    if handle_key in media_handles:
        return config.X_MEDIA_SCAN_LIMIT
    if handle_key in person_handles:
        return config.X_PERSON_SCAN_LIMIT
    return config.X_DEFAULT_SCAN_LIMIT


def _iter_account_tweets(
    handle: str,
    headers: dict[str, str],
    scan_limit: int,
    cutoff: datetime,
) -> list[dict[str, Any]]:
    tweets: list[dict[str, Any]] = []
    cursor = ""
    pages_fetched = 0
    max_pages = (scan_limit + 19) // 20

    while len(tweets) < scan_limit and pages_fetched < max_pages:
        params = {"userName": handle, "includeReplies": "false"}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            ACCOUNT_TWEETS_URL,
            headers=headers,
            params=params,
            timeout=(10, config.REQUEST_TIMEOUT),
        )
        resp.raise_for_status()
        payload = resp.json()
        pages_fetched += 1
        reached_cutoff = False

        for tweet in _tweet_records(payload):
            published = _created_at(tweet)
            if published and published.astimezone(timezone.utc) < cutoff:
                reached_cutoff = True
                continue
            tweets.append(tweet)
            if len(tweets) >= scan_limit:
                break

        cursor = str(payload.get("next_cursor") or "")
        if reached_cutoff:
            break
        if not payload.get("has_next_page") or not cursor:
            break

    return tweets


def _to_item(tweet: dict[str, Any], fallback_handle: str) -> PolicyItem | None:
    tweet_id = _tweet_id(tweet)
    text = _tweet_text(tweet)
    if not text or not _matches_keywords(text):
        return None
    if _is_low_signal_tweet_record(tweet, text):
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
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.X_LOOKBACK_HOURS)

    for handle in config.X_ACCOUNT_HANDLES:
        scan_limit = _scan_limit_for_handle(handle)
        logger.info(
            "Fetching up to %d tweets since %s for @%s via twitterapi.io",
            scan_limit,
            cutoff.strftime("%Y-%m-%d %H:%M UTC"),
            handle,
        )
        try:
            tweets = _iter_account_tweets(handle, headers, scan_limit, cutoff)
        except requests.RequestException as exc:
            logger.error("twitterapi.io fetch failed for @%s: %s", handle, exc)
            continue

        kept_for_account = 0
        for tweet in tweets:
            item = _to_item(tweet, handle)
            if not item:
                continue

            key = _tweet_id(tweet) or item.url
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            kept_for_account += 1

            if kept_for_account >= config.X_MAX_MATCHES_PER_ACCOUNT:
                break

    logger.info(
        "Collected %d matching X posts from %d account(s)",
        len(items),
        len(config.X_ACCOUNT_HANDLES),
    )
    return items
