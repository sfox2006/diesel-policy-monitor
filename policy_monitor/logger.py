"""
Centralised logging configuration.
Call setup_logging() once at startup (from main.py).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path

from policy_monitor import config

# ── macOS SSL fix ─────────────────────────────────────────────────────────────
# Python on macOS doesn't use the system keychain; point it to certifi's bundle.
try:
    import certifi
    _cafile = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", _cafile)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _cafile)
    # Patch the default SSL context so urllib (used by feedparser) picks it up
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=_cafile)
except ImportError:
    pass


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with rotating file handler + console handler."""
    root = logging.getLogger()
    if root.handlers:
        return  # Already configured — skip to prevent duplicate log lines

    log_file = config.LOG_DIR / f"policy_monitor_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root.setLevel(level)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotating file handler — max 5 MB, keep 7 rotations
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "feedparser", "chardet", "charset_normalizer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging initialised → %s", log_file)
