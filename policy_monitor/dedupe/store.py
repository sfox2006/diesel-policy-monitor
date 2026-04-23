"""
SQLite-backed deduplication store.

Strategy:
  1. Primary key  – normalised URL  (exact match)
  2. Secondary key – title fingerprint  (fuzzy: lowercase, punctuation stripped,
     first 120 chars hashed) catches same story from multiple sources.

Items seen within the last 7 days are considered "already sent".
Items older than 30 days are pruned from the database automatically.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)

_RETENTION_DAYS = 30
_DEDUPE_WINDOW_HOURS = 20  # within a single day's run


def _normalise_url(url: str) -> str:
    """Strip query params / fragments from URL for comparison."""
    from urllib.parse import urlparse, urlunparse
    p = urlparse(url.strip().lower())
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _title_fingerprint(title: str) -> str:
    """Stable hash of a normalised title."""
    clean = re.sub(r"[^a-z0-9 ]", "", title.lower())
    clean = re.sub(r"\s+", " ", clean).strip()[:120]
    return hashlib.sha1(clean.encode()).hexdigest()


class DedupeStore:
    """Thread-safe SQLite store for seen items."""

    def __init__(self, db_path: Path = config.DB_PATH) -> None:
        self._path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._prune_old()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url_key         TEXT NOT NULL UNIQUE,
                title_fp        TEXT NOT NULL,
                title           TEXT,
                source_name     TEXT,
                region          TEXT,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_title_fp ON seen_items (title_fp);
            CREATE INDEX IF NOT EXISTS idx_last_seen ON seen_items (last_seen);
            """
        )
        self._conn.commit()

    # ── Pruning ───────────────────────────────────────────────────────────────

    def _prune_old(self) -> None:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
        ).isoformat()
        cur = self._conn.execute(
            "DELETE FROM seen_items WHERE last_seen < ?", (cutoff,)
        )
        if cur.rowcount:
            logger.debug("Pruned %d old items from dedupe store", cur.rowcount)
        self._conn.commit()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_duplicate(self, item: PolicyItem) -> bool:
        """
        Return True if this item was already seen within _DEDUPE_WINDOW_HOURS.
        Also records the item if it's new.
        """
        url_key = _normalise_url(item.url)
        title_fp = _title_fingerprint(item.title)
        now = datetime.now(timezone.utc).isoformat()
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=_DEDUPE_WINDOW_HOURS)
        ).isoformat()

        # Check by URL
        row = self._conn.execute(
            "SELECT last_seen FROM seen_items WHERE url_key = ?", (url_key,)
        ).fetchone()
        if row and row["last_seen"] >= cutoff:
            return True

        # Check by title fingerprint (catches cross-source duplicates)
        row = self._conn.execute(
            "SELECT last_seen FROM seen_items WHERE title_fp = ? AND last_seen >= ?",
            (title_fp, cutoff),
        ).fetchone()
        if row:
            return True

        # New — record it
        self._conn.execute(
            """
            INSERT INTO seen_items (url_key, title_fp, title, source_name, region, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url_key) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (url_key, title_fp, item.title, item.source_name, item.region, now, now),
        )
        self._conn.commit()
        return False

    def filter_new(self, items: list[PolicyItem]) -> list[PolicyItem]:
        """Return only items that are NOT duplicates."""
        new_items: list[PolicyItem] = []
        dup_count = 0
        for item in items:
            if self.is_duplicate(item):
                dup_count += 1
            else:
                new_items.append(item)
        logger.info(
            "Deduplication: %d new, %d duplicates (from %d total)",
            len(new_items), dup_count, len(items),
        )
        return new_items

    def close(self) -> None:
        self._conn.close()
