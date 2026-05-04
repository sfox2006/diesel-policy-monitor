from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from policy_monitor.collectors.models import PolicyItem
from policy_monitor.summariser.briefing import generate_briefing


class BriefingTests(unittest.TestCase):
    def test_email_summary_keeps_x_signals_out_of_tldr_and_top_developments(self) -> None:
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
        article = PolicyItem(
            title="Government announces new diesel reserve rules",
            url="https://example.com/diesel-reserve-rules",
            source_name="Example News",
            region="Australia",
            source_type="secondary",
            topics=["reserves_and_prices"],
            published=datetime(2026, 5, 4, tzinfo=timezone.utc),
            summary="Government announces new diesel reserve rules.",
            score=35.0,
        )

        with tempfile.TemporaryDirectory() as tmp, \
            patch("policy_monitor.summariser.briefing.config.OUTPUT_DIR", Path(tmp)), \
            patch("policy_monitor.summariser.briefing.config.DEEP_DIVES_DIR", Path(tmp) / "deep_dives"), \
            patch("policy_monitor.summariser.briefing.config.TOP_DEVELOPMENTS", 5), \
            patch("policy_monitor.summariser.briefing.config.TLDR_BULLETS", 5), \
            patch("policy_monitor.summariser.briefing.config.X_SECTION_ITEMS", 5), \
            patch("policy_monitor.summariser.briefing.write_deep_dive", return_value=Path(tmp) / "deep.md"):
            Path(tmp, "deep_dives").mkdir()
            email_path, _, _ = generate_briefing([tweet, article])
            email = email_path.read_text(encoding="utf-8")

        tldr = email.split("## SECTION 1", 1)[1].split("## SECTION 2", 1)[0]
        top_developments = email.split("## SECTION 2", 1)[1].split("## SECTION 3", 1)[0]

        self.assertIn("SECTION 5", email)
        self.assertIn("X Signals", email)
        self.assertIn("X / Energy Minister (@energy_minister)", email)
        self.assertIn("https://x.com/energy_minister/status/123", email)
        self.assertNotIn("@energy_minister", tldr)
        self.assertNotIn("@energy_minister", top_developments)
        self.assertIn("Government announces new diesel reserve rules", tldr)


if __name__ == "__main__":
    unittest.main()
