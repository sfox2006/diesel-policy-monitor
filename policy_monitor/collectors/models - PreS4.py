"""
Shared data model for a collected policy item.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PolicyItem:
    title: str
    url: str
    source_name: str
    region: str
    source_type: str           # "primary" | "secondary"
    topics: list[str]
    published: datetime | None = None
    summary: str = ""          # short excerpt / description from source
    score: float = 0.0         # filled in by ranker
    is_watchlist: bool = False  # filled in by ranker
    deep_dive_path: str = ""   # filled in by briefing generator

    # ── helpers ──────────────────────────────────────────────────────────────
    @property
    def slug(self) -> str:
        """URL-safe slug for file names."""
        import re
        s = self.title.lower()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        s = s.strip("-")[:80]
        return s

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source_name": self.source_name,
            "region": self.region,
            "source_type": self.source_type,
            "topics": self.topics,
            "published": self.published.isoformat() if self.published else None,
            "summary": self.summary,
            "score": self.score,
            "is_watchlist": self.is_watchlist,
            "deep_dive_path": self.deep_dive_path,
        }
