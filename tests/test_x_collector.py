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
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_uses_person_scan_limit(self) -> None:
        tweets = [
            {
                "id": str(idx),
                "text": f"Diesel policy update {idx}",
                "author": {"userName": "minister"},
            }
            for idx in range(40)
        ]
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"tweets": tweets, "has_next_page": True, "next_cursor": "next"}

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_PERSON_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_MEDIA_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_PERSON_SCAN_LIMIT", 25), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 100), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 25)
        get.assert_called_once()

    def test_collect_x_posts_paginates_for_media_scan_limit(self) -> None:
        responses = []
        for page in range(7):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "tweets": [
                    {
                        "id": str((page * 20) + idx),
                        "text": f"Diesel market update {(page * 20) + idx}",
                        "author": {"userName": "Reuters"},
                    }
                    for idx in range(20)
                ],
                "has_next_page": True,
                "next_cursor": f"cursor-{page + 1}",
            }
            responses.append(response)

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["Reuters"]), \
            patch.object(x_collector.config, "X_PERSON_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_MEDIA_ACCOUNT_HANDLES", ["Reuters"]), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_MEDIA_SCAN_LIMIT", 125), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 200), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", side_effect=responses) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 125)
        self.assertEqual(get.call_count, 7)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["cursor"], "cursor-1")

    def test_collect_x_posts_uses_default_scan_limit_for_uncategorised_account(self) -> None:
        tweets = [
            {
                "id": str(idx),
                "text": f"Diesel policy update {idx}",
                "author": {"userName": "industry_body"},
            }
            for idx in range(30)
        ]
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"tweets": tweets, "has_next_page": True, "next_cursor": "next"}

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["industry_body"]), \
            patch.object(x_collector.config, "X_PERSON_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_MEDIA_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_DEFAULT_SCAN_LIMIT", 25), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 100), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 25)

    def test_collect_x_posts_ignores_older_tweets_even_under_scan_limit(self) -> None:
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        older = datetime.now(timezone.utc) - timedelta(hours=30)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "tweets": [
                {
                    "id": "recent",
                    "text": "Diesel policy update",
                    "createdAt": recent.isoformat(),
                    "author": {"userName": "minister"},
                },
                {
                    "id": "old",
                    "text": "Diesel policy update from last week",
                    "createdAt": older.isoformat(),
                    "author": {"userName": "minister"},
                },
            ],
            "has_next_page": False,
            "next_cursor": "",
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_PERSON_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_MEDIA_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_PERSON_SCAN_LIMIT", 25), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", return_value=response):
            items = x_collector.collect_x_posts()

        self.assertEqual([item.url for item in items], ["https://x.com/minister/status/recent"])

    def test_collect_x_posts_paginates_until_lookback_cutoff_when_under_limit(self) -> None:
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        older = datetime.now(timezone.utc) - timedelta(hours=30)
        first = Mock()
        first.raise_for_status.return_value = None
        first.json.return_value = {
            "tweets": [
                {
                    "id": str(idx),
                    "text": f"Diesel policy update {idx}",
                    "createdAt": recent.isoformat(),
                    "author": {"userName": "minister"},
                }
                for idx in range(10)
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
                    "text": "Diesel policy update old",
                    "createdAt": older.isoformat(),
                    "author": {"userName": "minister"},
                }
            ],
            "has_next_page": True,
            "next_cursor": "cursor-2",
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_PERSON_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_MEDIA_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_PERSON_SCAN_LIMIT", 25), \
            patch.object(x_collector.config, "X_LOOKBACK_HOURS", 24), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 100), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", side_effect=[first, second]) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 10)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["cursor"], "cursor-1")

    def test_collect_x_posts_stops_at_scan_limit_when_paging(self) -> None:
        first = Mock()
        first.raise_for_status.return_value = None
        first.json.return_value = {
            "tweets": [
                {
                    "id": str(idx),
                    "text": f"Diesel policy update {idx}",
                    "author": {"userName": "minister"},
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
                    "id": str(idx),
                    "text": f"Diesel policy update {idx}",
                    "author": {"userName": "minister"},
                }
                for idx in range(20, 40)
            ],
            "has_next_page": False,
            "next_cursor": "",
        }

        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_PERSON_ACCOUNT_HANDLES", ["minister"]), \
            patch.object(x_collector.config, "X_MEDIA_ACCOUNT_HANDLES", []), \
            patch.object(x_collector.config, "X_KEYWORDS", ["diesel"]), \
            patch.object(x_collector.config, "X_PERSON_SCAN_LIMIT", 25), \
            patch.object(x_collector.config, "X_MAX_MATCHES_PER_ACCOUNT", 100), \
            patch.object(x_collector.config, "X_INCLUDE_RETWEETS", False), \
            patch("policy_monitor.collectors.x_collector.requests.get", side_effect=[first, second]) as get:
            items = x_collector.collect_x_posts()

        self.assertEqual(len(items), 25)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["cursor"], "cursor-1")

    def test_collect_x_posts_skips_when_token_missing(self) -> None:
        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", ""):
            self.assertEqual(x_collector.collect_x_posts(), [])

    def test_collect_x_posts_skips_when_accounts_missing(self) -> None:
        with patch.object(x_collector.config, "TWITTERAPI_IO_KEY", "token"), \
            patch.object(x_collector.config, "X_ACCOUNT_HANDLES", []):
            self.assertEqual(x_collector.collect_x_posts(), [])


if __name__ == "__main__":
    unittest.main()
