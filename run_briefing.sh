#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run_briefing.sh
# Wrapper script called by cron (macOS/Linux).
# Edit PROJ_DIR and VENV_DIR to match your setup.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJ_DIR="$HOME/policy monitor"
VENV_DIR="$PROJ_DIR/.venv"
LOG_FILE="$PROJ_DIR/logs/cron.log"

echo "──────────────────────────────────────────" >> "$LOG_FILE"
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC')  Starting PolicyMonitor" >> "$LOG_FILE"

cd "$PROJ_DIR"
source "$VENV_DIR/bin/activate"

# Daily briefing
python main.py >> "$LOG_FILE" 2>&1

# Weekly outlook — runs every Sunday (weekday 6); cron fires daily at 06:00 AEST
DAY_OF_WEEK=$(date +%u)  # 1=Mon … 7=Sun
if [ "$DAY_OF_WEEK" -eq 7 ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC')  Running weekly outlook…" >> "$LOG_FILE"
    python -c "
from policy_monitor.summariser.weekly_briefing import generate_weekly_briefing
from policy_monitor.emailer.sender import send_briefing
from datetime import datetime; from zoneinfo import ZoneInfo
sydney = ZoneInfo('Australia/Sydney')
email_path, full_path = generate_weekly_briefing()
send_briefing(email_path, full_path,
    date_str=datetime.now(sydney).strftime('Week of %d %B %Y'),
    subject_prefix='Weekly Industrial Policy Outlook')
" >> "$LOG_FILE" 2>&1
fi

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC')  Done" >> "$LOG_FILE"
