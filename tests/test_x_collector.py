from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from policy_monitor.collectors import x_collector


class XCollectorTests(unittest.TestCase):
    def test_collect_x_posts_maps_api_response_to_policy_item(self) -> None:
        payload = {
            "tweets": [
                {
                    "id": "123",
                    "text": "Diesel supplies remain tight near the Strait of Hormuz",
                    "createdAt": "2026-05-04T00:00:00Z",
                    "author": {"name": "Energy Minister", "userName": "energy_minister"},
                    "likeCount": 5,
                    "retweetCount": 2,
                    "replyCount": 1,
                    "quoteCount": 0,
                }
            ],
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["energy_minister"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel", "Strait of Hormuz"]), \
            patch.object(x_collector.config, "X_MAX_RESULTS", 10), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_name, "X / Energy Minister (@energy_minister)")
        self.assertEqual(items[0].url, "https://x.com/energy_minister/status/123")
        self.assertIn("x_mentions", items[0].topics)
        self.assertEqual(items[0].published, datetime(2026, 5, 4, tzinfo=timezone.utc))
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["headers"], {"X-API-Key": "token"})
        self.assertEqual(get.call_args.kwargs["params"], {"userName": "energy_minister"})

    def test_collect_x_posts_filters_unrelated_tweets(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "tweets": [
                    {
                        "id": "124",
                        "text": "General campaign update with no fuel signal",
                        "author": {"userName": "leader"},
                    }
                ]
            }
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["leader"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel", "refinery"]), \
            patch.object(x_collector.config, "X_MAX_RESULTS", 10), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_skips_when_token_missing(self) -> None:
        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", ""):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_skips_when_accounts_missing(self) -> None:
        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", []):
            self.assertEqual(x_collector.collect_x_posts(), [])


if __name__ == "__main__":
    unittest.main()
