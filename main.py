#!/usr/bin/env python3
"""
PolicyMonitor — main entry point.

Run directly:
    python main.py

Or via cron / Task Scheduler (see README for setup).

Workflow:
    1. Collect from all RSS + HTML sources
    2. Deduplicate against SQLite store
    3. Score and rank by policy importance
    4. Generate email_summary.md, full_briefing.md, items.json, deep_dives/
    5. Send email briefing
"""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime, timezone

# ── Bootstrap logging FIRST ──────────────────────────────────────────────────
from policy_monitor.logger import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

# ── Now import the rest ───────────────────────────────────────────────────────
from policy_monitor import config
from policy_monitor.collectors.runner import run_all_collectors
from policy_monitor.dedupe.store import DedupeStore
from policy_monitor.emailer.sender import send_briefing
from policy_monitor.ranking.scorer import rank_items
from policy_monitor.summariser.briefing import generate_briefing


def run() -> None:
    start = datetime.now(timezone.utc)
    logger.info("=" * 70)
    logger.info("PolicyMonitor run started  %s", start.strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("=" * 70)

    # ── Step 1: Collect ───────────────────────────────────────────────────────
    logger.info("STEP 1/5  Collecting from %d sources…", len(__import__(
        "policy_monitor.collectors.sources", fromlist=["SOURCES"]
    ).SOURCES))
    raw_items = run_all_collectors()
    logger.info("  Raw items collected: %d", len(raw_items))

    if not raw_items:
        logger.warning("No items collected — aborting run.")
        return

    # Cap total items for performance
    raw_items = raw_items[: config.MAX_ITEMS_PER_RUN]

    # ── Step 2: Deduplicate ───────────────────────────────────────────────────
    logger.info("STEP 2/5  Deduplicating…")
    store = DedupeStore()
    try:
        new_items = store.filter_new(raw_items)
    finally:
        store.close()

    if not new_items:
        logger.info("All items already seen — nothing new to report. Skipping email.")
        return

    # ── Step 3: Rank ──────────────────────────────────────────────────────────
    logger.info("STEP 3/5  Ranking %d new items…", len(new_items))
    ranked = rank_items(new_items)

    # ── Step 4: Generate briefing ─────────────────────────────────────────────
    logger.info("STEP 4/5  Generating briefing…")
    email_path, full_path, json_path = generate_briefing(ranked)
    logger.info("  Outputs: %s  |  %s  |  %s", email_path, full_path, json_path)

    # ── Step 5: Send email ────────────────────────────────────────────────────
    logger.info("STEP 5/5  Sending email to %s…", config.EMAIL_TO)
    date_str = start.strftime("%d %B %Y")
    try:
        send_briefing(email_path, full_path, date_str=date_str)
    except Exception:
        logger.error("Email send failed — briefing is still saved locally.")
        logger.error(traceback.format_exc())

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("=" * 70)
    logger.info("Run complete in %.1f seconds.", elapsed)
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception:
        logger.critical("Unhandled exception:\n%s", traceback.format_exc())
        sys.exit(1)
