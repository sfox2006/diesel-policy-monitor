from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from policy_monitor.collectors import x_collector


class XCollectorTests(unittest.TestCase):
    def test_collect_x_posts_maps_api_response_to_policy_item(self) -> None:
        payload = {
            "data": [
                {
                    "id": "123",
                    "text": "Diesel supplies remain tight near the Strait of Hormuz",
                    "author_id": "u1",
                    "created_at": "2026-05-04T00:00:00Z",
                    "public_metrics": {
                        "like_count": 5,
                        "retweet_count": 2,
                        "reply_count": 1,
                        "quote_count": 0,
                    },
                }
            ],
            "includes": {
                "users": [
                    {"id": "u1", "name": "Energy Minister", "username": "energy_minister"}
                ]
            },
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload

        with patch.object(x_collector.config, "X_BEARER_TOKEN", "token"), \
            patch.object(x_collector.config, "X_SEARCH_QUERIES", ["diesel lang:en"]), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_MAX_RESULTS", 10), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_name, "X / Energy Minister (@energy_minister)")
        self.assertEqual(items[0].url, "https://x.com/energy_minister/status/123")
        self.assertIn("x_mentions", items[0].topics)
        self.assertEqual(items[0].published, datetime(2026, 5, 4, tzinfo=timezone.utc))

    def test_collect_x_posts_skips_when_token_missing(self) -> None:
        with patch.object(x_collector.config, "X_BEARER_TOKEN", ""):
            self.assertEqual(x_collector.collect_x_posts(), [])


if __name__ == "__main__":
    unittest.main()
