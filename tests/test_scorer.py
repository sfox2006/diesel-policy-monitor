from datetime import datetime, timezone
import unittest

from policy_monitor.collectors.models import PolicyItem
from policy_monitor.ranking.scorer import rank_items, score_item


def item(title: str, summary: str = "", source_type: str = "secondary") -> PolicyItem:
    return PolicyItem(
        title=title,
        url="https://example.com/story",
        source_name="Example Source",
        region="Australia",
        source_type=source_type,
        topics=["reserves_and_prices", "supply_disruption"],
        published=datetime.now(timezone.utc),
        summary=summary,
    )


class ScorerTests(unittest.TestCase):
    def test_scores_direct_diesel_supply_story(self) -> None:
        story = item(
            "Two Russian diesel cargoes bound for Brazil pivot toward Egypt",
            "Tankers carrying diesel and other refined petroleum products changed destination.",
        )

        self.assertGreaterEqual(score_item(story), 25.0)

    def test_rejects_generic_lng_energy_security_story(self) -> None:
        story = item(
            "Singapore deal highlights strategic importance of LNG exports",
            "The gas industry said LNG exports support regional energy security and mentioned liquid fuels once.",
        )

        self.assertEqual(score_item(story), 0.0)

    def test_rank_items_filters_zero_score_noise(self) -> None:
        relevant = item("Diesel reserve release planned after fuel stockholding review")
        noise = item("Small modular reactors under development in the United States")

        ranked = rank_items([noise, relevant])

        self.assertEqual([i.title for i in ranked], [relevant.title])


if __name__ == "__main__":
    unittest.main()
