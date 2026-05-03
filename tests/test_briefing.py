from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from policy_monitor.collectors.models import PolicyItem
from policy_monitor.summariser.briefing import generate_briefing


class BriefingTests(unittest.TestCase):
    def test_email_summary_contains_x_signals_section(self) -> None:
        tweet = PolicyItem(
            title="@energy_minister: Diesel supplies remain tight near Hormuz",
            url="https://x.com/energy_minister/status/123",
            source_name="X / Energy Minister (@energy_minister)",
            region="X",
            source_type="secondary",
            topics=["x_mentions", "supply_disruption"],
            published=datetime(2026, 5, 4, tzinfo=timezone.utc),
            summary="@energy_minister: Diesel supplies remain tight near Hormuz.",
            score=42.0,
        )

        with tempfile.TemporaryDirectory() as tmp, \
            patch("policy_monitor.summariser.briefing.config.OUTPUT_DIR", Path(tmp)), \
            patch("policy_monitor.summariser.briefing.config.DEEP_DIVES_DIR", Path(tmp) / "deep_dives"), \
            patch("policy_monitor.summariser.briefing.config.X_SECTION_ITEMS", 5), \
            patch("policy_monitor.summariser.briefing.write_deep_dive", return_value=Path(tmp) / "deep.md"):
            Path(tmp, "deep_dives").mkdir()
            email_path, _, _ = generate_briefing([tweet])
            email = email_path.read_text(encoding="utf-8")

        self.assertIn("SECTION 5 — X Signals", email)
        self.assertIn("X / Energy Minister (@energy_minister)", email)
        self.assertIn("https://x.com/energy_minister/status/123", email)


if __name__ == "__main__":
    unittest.main()
