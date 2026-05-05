# PolicyMonitor — Daily Industrial Policy Briefing

Lightweight Python system that collects policy developments from 40+ sources,
deduplicates, scores by relevance, and emails a concise daily briefing to
`ahmed.jawad@mandalapartners.com`.

---

## Repository Structure

```
policy monitor/
├── main.py                          # Main entry point (run this)
├── scheduler.py                     # Optional in-process daily scheduler
├── run_briefing.sh                  # macOS / Linux cron wrapper
├── run_briefing.bat                 # Windows Task Scheduler wrapper
├── requirements.txt
├── .env.example                     # Copy to .env and fill in
├── policy_monitor/
│   ├── config.py                    # All settings from .env
│   ├── logger.py                    # Logging setup
│   ├── collectors/
│   │   ├── sources.py               # 40+ source catalogue (RSS + scrape)
│   │   ├── models.py                # PolicyItem dataclass
│   │   ├── rss_collector.py         # feedparser-based RSS collector
│   │   ├── html_collector.py        # requests + BeautifulSoup scraper
│   │   └── runner.py                # Dispatches all sources, returns items
│   ├── dedupe/
│   │   └── store.py                 # SQLite deduplication (URL + title hash)
│   ├── ranking/
│   │   └── scorer.py                # Keyword scoring + region diversity
│   ├── summariser/
│   │   ├── briefing.py              # Generates email_summary.md + full_briefing.md
│   │   └── deep_dive.py             # Per-item deep-dive Markdown files
│   └── emailer/
│       └── sender.py                # SMTP sender (plain text + HTML + attachment)
├── output/
│   ├── email_summary.md             # Email body (regenerated each run)
│   ├── full_briefing.md             # All ranked items (attached to email)
│   ├── items.json                   # Machine-readable dump
│   └── deep_dives/                  # One .md per top development
└── logs/                            # Rotating log files
```

---

## 1. Installation

### Requirements
- Python 3.11+
- A Gmail account with **App Passwords** enabled (see below)

### Steps

```bash
# Clone / download the project
cd "policy monitor"

# Create virtual environment
python3.11 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
# Required: SMTP credentials (Office 365 / Outlook)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=ahmed.jawad@mandalapartners.com
SMTP_PASSWORD=your_outlook_password
EMAIL_FROM=ahmed.jawad@mandalapartners.com
EMAIL_TO=ahmed.jawad@mandalapartners.com
```

### Office 365 — SMTP AUTH setup

Office 365 business accounts have **SMTP AUTH disabled by default**. One of these must be true before the script can send:

**Option A — IT enables it for your mailbox (most reliable)**

Ask your IT admin to run this in Exchange Online PowerShell:
```powershell
Set-CASMailbox -Identity ahmed.jawad@mandalapartners.com -SmtpClientAuthenticationDisabled $false
```

**Option B — You use an Outlook App Password (if MFA is on)**

1. Go to [mysignins.microsoft.com/security-info](https://mysignins.microsoft.com/security-info)
2. Add sign-in method → App password
3. Copy the generated password into `SMTP_PASSWORD`

**Option C — Run the script from a personal Gmail account (no IT needed)**

If IT won't enable SMTP AUTH, use a Gmail account as the relay:
```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_personal_gmail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx     # Gmail App Password
EMAIL_FROM=your_personal_gmail@gmail.com
EMAIL_TO=ahmed.jawad@mandalapartners.com   # still delivers to your work inbox
```

> **Check if SMTP AUTH is already enabled:** Try running `python main.py` — if you get `SMTPAuthenticationError`, SMTP AUTH is blocked and you need Option A or C.

---

### Optional twitterapi.io monitoring

Add your twitterapi.io API key as a GitHub Actions repository secret named:

```text
TWITTERAPI_IO_KEY
```

Optional GitHub Actions repository variables:

```text
X_ACCOUNT_HANDLES     # comma-separated handles without @; defaults to the built-in watchlist
X_PERSON_ACCOUNT_HANDLES # handles scanned with the person limit
X_MEDIA_ACCOUNT_HANDLES  # handles scanned with the media limit
X_LOW_CAP_ACCOUNT_HANDLES # handles scanned with the low-volume account limit
X_KEYWORDS            # comma-separated local keyword filter
X_MAX_MATCHES_PER_ACCOUNT # default 500 matching tweets kept per account
X_DEFAULT_SCAN_LIMIT  # default 25 recent tweets for uncategorised accounts
X_PERSON_SCAN_LIMIT   # default 25 recent tweets for individual/person accounts
X_MEDIA_SCAN_LIMIT    # default 125 recent tweets for media accounts
X_LOW_CAP_SCAN_LIMIT  # default 5 recent tweets for nominated industry/union accounts
X_LOOKBACK_HOURS      # default 24; older tweets are ignored even if under the scan limit
X_INCLUDE_RETWEETS    # default false
X_SECTION_ITEMS       # default 8
```

The default account watchlist includes Australian ministers/regulators, energy and shipping bodies, Reuters, ABC Politics, AFR, Al Jazeera English, FT Energy, WSJ Energy and regional media, plus selected US, Iran, Japan, Malaysia, Singapore, Thailand, industry, transport, agriculture, mining, construction, and union accounts. The monitor calls twitterapi.io's selected-account timeline endpoint for each `X_ACCOUNT_HANDLES` entry and scans tweets from the last 24 hours, capped at the most recent 25 tweets for individual/person accounts, 125 tweets for media accounts, and 5 tweets for nominated industry/union accounts by default. Older tweets are ignored even when the account has fewer tweets than its cap. It keeps only tweets matching `X_KEYWORDS` such as diesel, petrol, fuel, refineries, and the Strait of Hormuz, and filters obvious podcast/audio posts using phrases and domains such as Spotify, Apple Podcasts, SoundCloud, Acast, Omny, and similar links.

---

## 3. Run Manually

```bash
# Activate venv first
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

python main.py
```

Expected output:
```
2026-03-08 07:00:00  INFO  __main__  ══ PolicyMonitor run started 2026-03-08 07:00 UTC
2026-03-08 07:00:00  INFO  __main__  STEP 1/5  Collecting from 40 sources…
...
2026-03-08 07:02:30  INFO  __main__  STEP 5/5  Sending email to ['ahmed.jawad@mandalapartners.com']…
2026-03-08 07:02:35  INFO  __main__  Run complete in 155.3 seconds.
```

---

## 4. macOS / Linux — cron Job

### Option A: cron (recommended)

```bash
# Open crontab
crontab -e

# Fire every day at 07:00 UTC
0 7 * * * /bin/bash "/Users/ahmedjawad/policy monitor/run_briefing.sh"
```

Verify cron has Full Disk Access on macOS:
- System Settings → Privacy & Security → Full Disk Access → add `/usr/sbin/cron`

### Option B: launchd (macOS native)

Create `~/Library/LaunchAgents/com.mandala.policymonitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mandala.policymonitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/ahmedjawad/policy monitor/run_briefing.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/ahmedjawad/policy monitor/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/ahmedjawad/policy monitor/logs/launchd_err.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.mandala.policymonitor.plist
```

---

## 5. Windows — Task Scheduler

1. Edit `run_briefing.bat` — update `PROJ_DIR` to your actual path.

2. Open **Task Scheduler** (`taskschd.msc`)

3. **Create Basic Task:**
   - Name: `PolicyMonitor Daily Briefing`
   - Trigger: **Daily** at 07:00 AM (adjust timezone as needed)
   - Action: **Start a program**
     - Program: `C:\Users\YourName\policy monitor\run_briefing.bat`
     - Start in: `C:\Users\YourName\policy monitor`

4. In **General** tab:
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"

5. Click **OK**, enter your Windows password when prompted.

**Verify it works:**
- Right-click the task → **Run**
- Check `logs\task_scheduler.log` for output

---

## 6. In-Process Scheduler (alternative to cron)

If you prefer not to use cron / Task Scheduler:

```bash
# Fire at 07:00 UTC every day
python scheduler.py

# Custom time
python scheduler.py --time 06:30

# Run immediately, then keep running on schedule
python scheduler.py --now
```

Run this in a persistent terminal (tmux, screen, or a systemd service).

---

## 7. Output Files

| File | Description |
|------|-------------|
| `output/email_summary.md` | Email body — TL;DR, Top 5, Watchlist |
| `output/full_briefing.md` | All ranked items with metadata |
| `output/items.json` | Machine-readable JSON of all items |
| `output/deep_dives/*.md` | One file per Top Development |
| `logs/policy_monitor_YYYY-MM-DD.log` | Daily rotating log |

---

## 8. Email Structure

**Subject:** `Daily Industrial Policy Briefing — 08 March 2026`

**Body:**

```
SECTION 1 — TL;DR (6 bullets)
  [Region] Headline → One-sentence summary

SECTION 2 — Top Developments (5 items)
  Headline
  2-3 sentence summary (what happened / why it matters)
  Source links
  Deep dive path

SECTION 3 — Watchlist (3 items)
  Upcoming votes, consultations, regulatory deadlines

Attachment: full_briefing_2026-03-08.md
```

---

## 9. Customisation

### Add or remove sources
Edit [policy_monitor/collectors/sources.py](policy_monitor/collectors/sources.py).
Each source entry takes:
```python
{
    "name": "Source Name",
    "region": "Europe",        # Americas | Europe | Asia | AsiaPacific | Gulf | Global
    "type": "primary",         # primary | secondary
    "feed": "https://...",     # RSS/Atom URL (preferred)
    "scrape_url": "https://…", # fallback HTML page
    "scrape_cfg": {            # CSS selectors for HTML scraping
        "list_selector": "div.article",
        "title": "h3",
        "link": "a",
    },
    "topics": ["industrial_policy", "critical_minerals"],
}
```

### Adjust scoring weights
Edit [policy_monitor/ranking/scorer.py](policy_monitor/ranking/scorer.py).
Add keyword patterns to `PRIORITY_PATTERNS` or adjust weights.

### Change briefing length
Edit `.env`:
```dotenv
TOP_DEVELOPMENTS=5
WATCHLIST_ITEMS=3
TLDR_BULLETS=6
```

---

## 10. Troubleshooting

| Problem | Fix |
|---------|-----|
| `SMTP authentication failed` | Office 365: ask IT to enable SMTP AUTH for your mailbox, or use a Gmail relay account (see Section 2) |
| `No items collected` | Check your internet connection; some feeds may be temporarily down |
| `All items already seen` | Normal if run twice in one day — dedupe window is 20 hours |
| `HTML scrape returns 0 items` | Target site may have changed layout — update `scrape_cfg` selectors |
| Import errors | Ensure venv is activated and `pip install -r requirements.txt` was run |

---

*PolicyMonitor — built for Mandala Partners*
