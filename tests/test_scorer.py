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

    def test_scores_taiwan_refined_fuel_supply_story(self) -> None:
        story = item(
            "Taiwan confirms diesel and petroleum reserve coverage after shipping disruption",
            "MOEA said CPC Corporation is monitoring fuel imports and refinery supply.",
            source_type="primary",
        )

        self.assertGreaterEqual(score_item(story), 25.0)

    def test_rejects_generic_industrial_supply_chain_policy(self) -> None:
        story = item(
            "Japan and Korea announce semiconductor supply chain cooperation",
            "The prime ministers said the industrial partnership will support regional manufacturing resilience.",
            source_type="primary",
        )

        self.assertEqual(score_item(story), 0.0)

    def test_scores_senior_government_fuel_announcement(self) -> None:
        story = item(
            "Prime Minister announces diesel reserve release after refinery outage",
            "The energy minister said fuel imports and petroleum stocks will be monitored daily.",
            source_type="primary",
        )

        self.assertGreaterEqual(score_item(story), 25.0)

    def test_rejects_fuel_adjacent_company_market_story(self) -> None:
        story = item(
            "Chevron to close deal for Singapore refinery stake sale",
            "Both parties are reassessing offtake agreements for refined products.",
        )

        self.assertEqual(score_item(story), 0.0)

    def test_rejects_biofuel_feedstock_market_story(self) -> None:
        story = item(
            "China's used cooking oil ships to US as war drives biofuel boom",
            "Fuel makers are acquiring feedstocks to churn out renewable diesel.",
        )

        self.assertEqual(score_item(story), 0.0)

    def test_rank_items_filters_zero_score_noise(self) -> None:
        relevant = item("Diesel reserve release planned after fuel stockholding review")
        noise = item("Small modular reactors under development in the United States")

        ranked = rank_items([noise, relevant])

        self.assertEqual([i.title for i in ranked], [relevant.title])


if __name__ == "__main__":
    unittest.main()
