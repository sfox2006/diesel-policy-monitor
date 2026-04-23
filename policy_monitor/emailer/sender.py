"""
Email sender using Python's built-in smtplib (SMTP with STARTTLS).

Sends a multipart email with:
  • Plain-text fallback (Markdown stripped to plain)
  • HTML body (Markdown converted, Mandala colour scheme)
  • Briefing .md attached

Requires environment variables defined in .env (see config.py).
"""

from __future__ import annotations

import logging
import re
import smtplib
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from policy_monitor import config

logger = logging.getLogger(__name__)

# ── Mandala colour palette ────────────────────────────────────────────────────
# Deep navy primary, warm gold accent, off-white background

_C = {
    "navy":        "#1C2B4A",   # primary brand colour
    "gold":        "#B8960C",   # accent / section markers
    "gold_light":  "#C9A84C",   # links, h3
    "bg":          "#F6F4EF",   # warm off-white body background
    "card":        "#FFFFFF",   # content card background
    "border":      "#DDD8CC",   # dividers
    "text":        "#1A1A1A",   # body text
    "meta":        "#6B7280",   # timestamps, metadata
    "header_bg":   "#1C2B4A",   # email header banner
    "header_text": "#F6F4EF",   # text on header banner
}


# ── Markdown → HTML ───────────────────────────────────────────────────────────

def _md_to_html(md: str, is_weekly: bool = False) -> str:
    """Convert Markdown to styled HTML with Mandala colour scheme."""
    lines = md.split("\n")
    html_lines: list[str] = []
    in_ul = False

    for line in lines:
        if line.startswith("### "):
            if in_ul:
                html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h3 class="h3">{_inline(line[4:])}</h3>')
        elif line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h2 class="h2">{_inline(line[3:])}</h2>')
        elif line.startswith("# "):
            if in_ul:
                html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h1 class="h1">{_inline(line[2:])}</h1>')
        elif line.strip() == "---":
            if in_ul:
                html_lines.append("</ul>"); in_ul = False
            html_lines.append('<hr class="divider">')
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                html_lines.append('<ul class="list">'); in_ul = True
            html_lines.append(f"  <li>{_inline(line[2:])}</li>")
        elif not line.strip():
            if in_ul:
                html_lines.append("</ul>"); in_ul = False
            html_lines.append('<div class="spacer"></div>')
        else:
            if in_ul:
                html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<p class="para">{_inline(line)}</p>')

    if in_ul:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)
    accent_label = "WEEKLY OUTLOOK" if is_weekly else "DAILY BRIEFING"
    timestamp = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>

  /* ── Reset ── */
  body, table, td, p, a, li {{ margin:0; padding:0; border:0; }}
  body {{
    background-color: {_C["bg"]};
    font-family: 'Georgia', 'Times New Roman', serif;
    color: {_C["text"]};
    -webkit-text-size-adjust: 100%;
  }}

  /* ── Outer wrapper ── */
  .wrapper {{
    max-width: 700px;
    margin: 0 auto;
    background: {_C["bg"]};
  }}

  /* ── Header banner ── */
  .header {{
    background-color: {_C["navy"]};
    padding: 28px 36px 24px;
    border-bottom: 4px solid {_C["gold"]};
  }}
  .header-brand {{
    font-family: 'Georgia', serif;
    font-size: 11px;
    font-weight: normal;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: {_C["gold"]};
    margin-bottom: 6px;
  }}
  .header-title {{
    font-size: 13px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {_C["header_text"]};
    opacity: 0.75;
  }}

  /* ── Content card ── */
  .card {{
    background: {_C["card"]};
    margin: 0;
    padding: 32px 36px 24px;
    border-left: 4px solid {_C["gold"]};
  }}

  /* ── Typography ── */
  .h1 {{
    font-size: 20px;
    font-weight: bold;
    color: {_C["navy"]};
    border-bottom: 2px solid {_C["gold"]};
    padding-bottom: 10px;
    margin: 0 0 16px;
    line-height: 1.3;
  }}
  .h2 {{
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: {_C["gold"]};
    margin: 28px 0 10px;
    padding-top: 4px;
  }}
  .h3 {{
    font-size: 15px;
    font-weight: bold;
    color: {_C["navy"]};
    margin: 18px 0 6px;
    line-height: 1.4;
  }}
  .para {{
    font-size: 14px;
    line-height: 1.7;
    color: {_C["text"]};
    margin: 6px 0;
  }}
  .list {{
    padding-left: 18px;
    margin: 6px 0 10px;
  }}
  .list li {{
    font-size: 14px;
    line-height: 1.7;
    margin-bottom: 5px;
    color: {_C["text"]};
  }}
  a {{
    color: {_C["gold_light"]};
    text-decoration: none;
  }}
  a:hover {{ text-decoration: underline; }}
  .divider {{
    border: none;
    border-top: 1px solid {_C["border"]};
    margin: 22px 0;
  }}
  .spacer {{ height: 6px; }}
  code {{
    background: {_C["bg"]};
    border: 1px solid {_C["border"]};
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 12px;
    font-family: 'Courier New', monospace;
  }}
  em {{ color: {_C["meta"]}; font-style: italic; font-size: 13px; }}

  /* ── Footer ── */
  .footer {{
    background-color: {_C["navy"]};
    padding: 16px 36px;
    border-top: 1px solid rgba(200,160,12,0.3);
  }}
  .footer p {{
    font-size: 11px;
    color: rgba(246,244,239,0.5);
    line-height: 1.6;
    letter-spacing: 0.3px;
  }}

</style>
</head>
<body>
<div class="wrapper">

  <!-- Header -->
  <div class="header">
    <div class="header-brand">Mandala Partners · Intelligence</div>
    <div class="header-title">{accent_label} · {timestamp}</div>
  </div>

  <!-- Content -->
  <div class="card">
    {body}
  </div>

  <!-- Footer -->
  <div class="footer">
    <p>
      Generated by PolicyMonitor · 241 sources across Americas, Europe, Asia-Pacific, Gulf &amp; Global ·
      Delivered daily at 06:00 AEST to ahmed.jawad@mandalapartners.com
    </p>
  </div>

</div>
</body>
</html>"""


def _inline(text: str) -> str:
    """Apply inline Markdown transforms (bold, italic, links, code)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _md_to_plain(md: str) -> str:
    """Strip Markdown syntax for plain-text fallback."""
    text = re.sub(r"#+\s*", "", md)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^---+$", "-" * 60, text, flags=re.MULTILINE)
    return text


# ── Main send function ────────────────────────────────────────────────────────

def send_briefing(
    email_md_path: Path,
    full_briefing_path: Path,
    date_str: str | None = None,
    subject_prefix: str = "Daily Industrial Policy Briefing",
) -> None:
    """
    Send the briefing email via SMTP (STARTTLS).

    Args:
        email_md_path:      Path to email summary markdown
        full_briefing_path: Path to full briefing markdown (attached)
        date_str:           Date string for subject line
        subject_prefix:     Subject prefix — changed to 'Weekly Industrial Policy Outlook'
                            for weekly sends
    """
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be set in the .env file. "
            "See .env.example for instructions."
        )

    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%d %B %Y")

    is_weekly = "Weekly" in subject_prefix
    subject = f"{subject_prefix} — {date_str}"
    md_body = email_md_path.read_text(encoding="utf-8")

    from_addr = config.EMAIL_FROM or config.SMTP_USER
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(config.EMAIL_TO)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(_md_to_plain(md_body), "plain", "utf-8"))
    alt.attach(MIMEText(_md_to_html(md_body, is_weekly=is_weekly), "html", "utf-8"))
    msg.attach(alt)

    if full_briefing_path.exists():
        prefix = "weekly" if is_weekly else "full_briefing"
        attachment_name = f"{prefix}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
        with open(full_briefing_path, "rb") as fh:
            part = MIMEBase("text", "markdown")
            part.set_payload(fh.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{attachment_name}"')
        msg.attach(part)
        logger.debug("Attached: %s", full_briefing_path)

    logger.info("Sending '%s' to %s via %s:%s…", subject, config.EMAIL_TO, config.SMTP_HOST, config.SMTP_PORT)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.ehlo(config.SMTP_HOST)
            server.starttls()
            server.ehlo(config.SMTP_HOST)
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(from_addr, config.EMAIL_TO, msg.as_bytes())
        logger.info("Email sent successfully.")
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed for %s. "
            "For Office 365: ask IT to enable SMTP AUTH "
            "(Set-CASMailbox -Identity %s -SmtpClientAuthenticationDisabled $false). "
            "Or use a Gmail App Password.",
            config.SMTP_USER, config.SMTP_USER,
        )
        raise
    except Exception as exc:
        logger.error("Failed to send email: %s", exc, exc_info=True)
        raise
