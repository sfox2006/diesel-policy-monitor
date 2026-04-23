#!/usr/bin/env python3
"""
PolicyMonitor daily scheduler — fires at 06:00 AEST (Sydney time) every day.

Handles daylight saving automatically: Sydney is UTC+11 (AEDT) Oct–Apr,
UTC+10 (AEST) Apr–Oct. The scheduler recomputes the UTC target each day.

Usage:
    python scheduler.py          # 06:00 Sydney time daily
    python scheduler.py --now    # run immediately, then keep on schedule
"""

from __future__ import annotations

import argparse
import logging
import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from policy_monitor.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

SYDNEY = ZoneInfo("Australia/Sydney")
FIRE_HOUR = 6    # 06:00 AEST/AEDT
FIRE_MINUTE = 0


def _next_fire() -> datetime:
    """Return the next 06:00 Sydney time as a UTC-aware datetime."""
    now_sydney = datetime.now(SYDNEY)
    target = now_sydney.replace(hour=FIRE_HOUR, minute=FIRE_MINUTE, second=0, microsecond=0)
    if now_sydney >= target:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc)


def _run_daily() -> None:
    try:
        from main import run
        logger.info("── Daily run ──────────────────────────────")
        run()
    except Exception:
        logger.error("Daily run failed:\n%s", traceback.format_exc())


def _run_weekly() -> None:
    try:
        from policy_monitor.summariser.weekly_briefing import generate_weekly_briefing
        from policy_monitor.emailer.sender import send_briefing
        logger.info("── Weekly run ─────────────────────────────")
        email_path, full_path = generate_weekly_briefing()
        date_str = datetime.now(SYDNEY).strftime("Week of %d %B %Y")
        send_briefing(
            email_path, full_path,
            date_str=date_str,
            subject_prefix="Weekly Industrial Policy Outlook",
        )
    except Exception:
        logger.error("Weekly run failed:\n%s", traceback.format_exc())


def _is_weekly_day() -> bool:
    """Return True if today (Sydney time) is the configured weekly day."""
    from policy_monitor import config
    return datetime.now(SYDNEY).weekday() == config.WEEKLY_DAY_OF_WEEK


def main() -> None:
    parser = argparse.ArgumentParser(description="PolicyMonitor scheduler")
    parser.add_argument("--now", action="store_true", help="Run immediately then schedule")
    args = parser.parse_args()

    logger.info(
        "Scheduler started — daily at 06:00 Sydney time (currently %s)",
        datetime.now(SYDNEY).strftime("%H:%M %Z"),
    )

    if args.now:
        logger.info("--now: running immediately…")
        _run_daily()
        if _is_weekly_day():
            _run_weekly()

    while True:
        next_utc = _next_fire()
        next_sydney = next_utc.astimezone(SYDNEY)
        logger.info("Next run: %s", next_sydney.strftime("%Y-%m-%d %H:%M %Z"))

        # Sleep until near the target, then tight-poll
        while True:
            now_utc = datetime.now(timezone.utc)
            remaining = (next_utc - now_utc).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(remaining - 60, 300) if remaining > 65 else 5)

        _run_daily()
        if _is_weekly_day():
            _run_weekly()

        # Pause to avoid double-firing within the same minute
        time.sleep(90)


if __name__ == "__main__":
    main()
