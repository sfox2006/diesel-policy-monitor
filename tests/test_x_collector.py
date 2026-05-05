from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock, patch

from policy_monitor.collectors import x_collector


class XCollectorTests(unittest.TestCase):
    def test_collect_x_posts_maps_api_response_to_policy_item(self) -> None:
        published = datetime.now(timezone.utc)
        payload = {
            "tweets": [
                {
                    "id": "123",
                    "text": "Diesel supplies remain tight near the Strait of Hormuz",
                    "createdAt": published.isoformat(),
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
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_MAX_SCAN_PAGES_PER_ACCOUNT", 20), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_name, "X / Energy Minister (@energy_minister)")
        self.assertEqual(items[0].url, "https://x.com/energy_minister/status/123")
        self.assertIn("x_mentions", items[0].topics)
        self.assertEqual(items[0].published, published)
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["headers"], {"X-API-Key": "token"})
        self.assertEqual(
            get.call_args.kwargs["params"],
            {"userName": "energy_minister", "includeReplies": "false"},
        )

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

    def test_collect_x_posts_filters_listen_tweets(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "tweets": [
                {
                    "id": "125",
                    "text": "Listen to our latest podcast on diesel and refinery markets",
                    "author": {"userName": "energy_podcast"},
                }
            ]
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["energy_podcast"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel", "refinery"]), \
            patch.object(x_collector.config, "X_MAX_RESULTS", 10), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_filters_podcast_links(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "tweets": [
                {
                    "id": "126",
                    "text": "Diesel and refinery market update",
                    "author": {"userName": "energy_podcast"},
                    "entities": {
                        "urls": [
                            {"expanded_url": "https://open.spotify.com/show/example"}
                        ]
                    },
                }
            ]
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["energy_podcast"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel", "refinery"]), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 10), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_MAX_SCAN_PAGES_PER_ACCOUNT", 20), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_skips_tweets_outside_lookback(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(hours=26)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "tweets": [
                {
                    "id": "old",
                    "text": "Diesel policy update",
                    "createdAt": old.isoformat(),
                    "author": {"userName": "minister"},
                }
            ],
            "has_next_page": False,
            "next_cursor": "",
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_MAX_SCAN_PAGES_PER_ACCOUNT", 20), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_paginates_until_it_reaches_lookback_cutoff(self) -> None:
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        older = datetime.now(timezone.utc) - timedelta(hours=26)
        first = Mock()
        first.raise_for_status.return_value = None
        first.json.return_value = {
            "tweets": [
                {
                    "id": str(idx),
                    "text": f"Diesel market update {idx}",
                    "createdAt": recent.isoformat(),
                    "author": {"userName": "Reuters"},
                }
                for idx in range(20)
            ],
            "has_next_page": True,
            "next_cursor": "cursor-1",
        }
        second = Mock()
        second.raise_for_status.return_value = None
        second.json.return_value = {
            "tweets": [
                {
                    "id": "old",
                    "text": "Diesel market update old",
                    "createdAt": older.isoformat(),
                    "author": {"userName": "Reuters"},
                }
            ],
            "has_next_page": True,
            "next_cursor": "cursor-2",
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["Reuters"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_MAX_SCAN_PAGES_PER_ACCOUNT", 20), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 100), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", side_effect=[first, second]) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 20)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["cursor"], "cursor-1")

    def test_collect_x_posts_stops_at_page_cap(self) -> None:
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        tweets = [
            {
                "id": str(idx),
                "text": f"Diesel policy update {idx}",
                "createdAt": recent.isoformat(),
                "author": {"userName": "minister"},
            }
            for idx in range(20)
        ]
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"tweets": tweets, "has_next_page": True, "next_cursor": "next"}

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_MAX_SCAN_PAGES_PER_ACCOUNT", 1), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 100), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 20)
        get.assert_called_once()

    def test_collect_x_posts_skips_when_token_missing(self) -> None:
        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", ""):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_skips_when_accounts_missing(self) -> None:
        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", []):
            self.assertEqual(x_collector.collect_x_posts(), [])


if __name__ == "__main__":
    unittest.main()
