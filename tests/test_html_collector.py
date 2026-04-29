import unittest

from bs4 import BeautifulSoup

from policy_monitor.collectors.html_collector import _extract_title_href


class HtmlCollectorTests(unittest.TestCase):
    def test_extracts_listing_when_row_is_anchor(self) -> None:
        soup = BeautifulSoup(
            '<a href="/business/202604290011">'
            "Taiwan fuel supply update"
            "</a>",
            "lxml",
        )

        title, href = _extract_title_href(
            soup.select_one("a"),
            "a",
            "a",
            "https://focustaiwan.tw/business",
        )

        self.assertEqual(title, "Taiwan fuel supply update")
        self.assertEqual(href, "https://focustaiwan.tw/business/202604290011")


if __name__ == "__main__":
    unittest.main()
