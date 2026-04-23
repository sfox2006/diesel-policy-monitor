"""
Source catalogue — Australian Diesel Fuel Security edition.

Each entry is a dict with:
  name        – human-readable label
  region      – geographic tag
  type        – "primary" | "secondary"
  feed        – RSS/Atom URL (preferred)
  scrape_url  – fallback HTML page (if no feed)
  scrape_cfg  – optional CSS-selector hints for scraper
  topics      – list of topic tags used in scoring

Topics (five briefing sections):
  reserves_and_prices    – domestic stock levels, wholesale/retail prices, AIP data
  shipments              – tanker movements, port activity, import volumes
  partner_country        – developments in Japan/Malaysia/Singapore/Korea/Thailand
                           affecting what Australia can import
  policy_and_legislation – bills, ministerial statements, IEA obligations,
                           DCCEEW/PM releases
  supply_disruption      – refinery outages, route disruptions, geopolitical
                           risk flags; weighted higher for urgency alerting

Regions used:
  Australia, Japan, Malaysia, Singapore, SouthKorea, Thailand, International

Removed from previous version:
  - Australian Energy Regulator (feed dead)
  - Reuters Business feed, Reuters Commodities feed (confirmed dead)
  - AFR, The Australian, Financial Times (paywalled)
  - Platts / S&P Global (blocks scraper)
  - World Bank, Infrastructure Australia (unreliable)
"""

from typing import TypedDict


class Source(TypedDict, total=False):
    name: str
    region: str
    type: str          # "primary" | "secondary"
    feed: str
    scrape_url: str
    scrape_cfg: dict
    topics: list[str]


SOURCES: list[Source] = [

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — Australian Government & Regulators
    # ══════════════════════════════════════════════════════════════════════════


    {
        "name": "Prime Minister's Office – Media Releases",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.pm.gov.au/media/rss",
        "topics": ["policy_and_legislation"],
    },
    {
        "name": "Australian Parliament – Bills",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.aph.gov.au/rss/Bills.aspx",
        "topics": ["policy_and_legislation"],
    },
    {
        "name": "Australian Parliament – Media Releases",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.aph.gov.au/rss/MediaReleases.aspx",
        "topics": ["policy_and_legislation"],
    },
    {
        "name": "Australian Parliament – Senate Daily Summary",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.aph.gov.au/rss/SenateBusinessSummary.aspx",
        "topics": ["policy_and_legislation"],
    },
    {
        "name": "Australian Treasury – Media Releases",
        "region": "Australia",
        "type": "primary",
        "feed": "https://treasury.gov.au/rss/media-releases.rss",
        "topics": ["policy_and_legislation", "reserves_and_prices"],
    },
    {
        "name": "Australian Competition and Consumer Commission – Media Releases",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.accc.gov.au/media-release/feed",
        "topics": ["reserves_and_prices", "policy_and_legislation"],
    },
    {
        "name": "Australian Bureau of Statistics – Economy",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.abs.gov.au/rss.xml",
        "topics": ["reserves_and_prices"],
    },
    
   
    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — Australian Industry Bodies
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "APPEA – News",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.appea.com.au/feed/",
        "topics": ["reserves_and_prices", "policy_and_legislation"],
    },
    {
        "name": "APPEA – Media Releases",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.appea.com.au/category/media-releases/feed/",
        "topics": ["reserves_and_prices", "policy_and_legislation"],
    },
    {
        "name": "Australian Institute of Petroleum – News",
        "region": "Australia",
        "type": "primary",
        # Primary data source for wholesale and retail diesel prices.
        "scrape_url": "https://www.aip.com.au/aip-news",
        "scrape_cfg": {"list_selector": "div.news-item", "title": "h3", "link": "a"},
        "topics": ["reserves_and_prices"],
    },
    {
        "name": "Australian Trucking Association – News",
        "region": "Australia",
        "type": "primary",
        # Useful for station outage signals and retail price pressure.
        "feed": "https://www.truck.net.au/feed",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner"],
    },
    {
        "name": "National Farmers Federation – News",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.nff.org.au/feed/",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner"],
    },
    {
        "name": "Minerals Council of Australia – News",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.minerals.org.au/feed/",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — International Energy Bodies
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "IEA – News",
        "region": "International",
        "type": "primary",
        "feed": "https://www.iea.org/feed",
        "topics": ["policy_and_legislation", "reserves_and_prices", "supply_disruption"],
    },
    {
        "name": "US EIA – Today in Energy",
        "region": "International",
        "type": "primary",
        "feed": "https://www.eia.gov/rss/todayinenergy.xml",
        "topics": ["reserves_and_prices", "shipments"],
    },
    {
        "name": "US DOE – Energy News",
        "region": "International",
        "type": "primary",
        "feed": "https://www.energy.gov/rss.xml",
        "topics": ["policy_and_legislation", "supply_disruption"],
    },
    {
        "name": "Asian Development Bank – News",
        "region": "International",
        "type": "primary",
        "feed": "https://www.adb.org/news/rss.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner"],
    },
    {
        "name": "PortWatch – Tanker & Shipment Tracking",
        "region": "International",
        "type": "primary",
        # IMF/Oxford PortWatch — cited directly in slide 3 as a data source
        # for tracking tanker movements and port activity into Australian ports.
        "scrape_url": "https://portwatch.imf.org",
        "scrape_cfg": {"list_selector": "div.update-item", "title": "h3", "link": "a"},
        "topics": ["shipments", "supply_disruption"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — Japan
    # ══════════════════════════════════════════════════════════════════════════


    {
        "name": "Japan Ministry of Foreign Affairs – News",
        "region": "Japan",
        "type": "primary",
        "feed": "https://www.mofa.go.jp/rss/rss.xml",
        "topics": ["partner_country", "supply_disruption"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — Malaysia
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "PETRONAS – Media Releases",
        "region": "Malaysia",
        "type": "primary",
        "scrape_url": "https://www.petronas.com/media/media-releases",
        "scrape_cfg": {"list_selector": "div.media-release-item", "title": "h3", "link": "a"},
        "topics": ["partner_country", "shipments", "supply_disruption"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — Singapore
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "Singapore Ministry of Trade and Industry – News",
        "region": "Singapore",
        "type": "primary",
        "feed": "https://www.mti.gov.sg/rss/news",
        "topics": ["partner_country", "shipments"],
    },
    {
        "name": "Singapore Ministry of Foreign Affairs – News",
        "region": "Singapore",
        "type": "primary",
        "feed": "https://www.mfa.gov.sg/Newsroom/rss",
        "topics": ["partner_country", "supply_disruption"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — South Korea
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "Korea Ministry of Foreign Affairs – News",
        "region": "SouthKorea",
        "type": "primary",
        "feed": "https://www.mofa.go.kr/eng/rss/engRss.do",
        "topics": ["partner_country", "supply_disruption"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PRIMARY — Thailand
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "PTT Public Company – Press Releases",
        "region": "Thailand",
        "type": "primary",
        "scrape_url": "https://www.pttplc.com/en/Media/Press-Release/Pages/default.aspx",
        "scrape_cfg": {"list_selector": "div.press-release-item", "title": "h3", "link": "a"},
        "topics": ["partner_country", "shipments", "supply_disruption"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — Australian Media (RSS confirmed working)
    # ══════════════════════════════════════════════════════════════════════════


    {
        "name": "ABC News – Politics",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.abc.net.au/news/feed/51892/rss.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Sydney Morning Herald – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.smh.com.au/rss/business.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Sydney Morning Herald – National",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.smh.com.au/rss/national.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "The Age – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.theage.com.au/rss/business.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "The Guardian Australia – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.theguardian.com/australia-news/business/rss",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "The Guardian Australia – Environment",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.theguardian.com/australia-news/environment/rss",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "RenewEconomy – Energy News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://reneweconomy.com.au/feed/",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Sky News Australia",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.skynews.com.au/rss.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — Regional / Partner Country Media
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "Japan Times – Business",
        "region": "Japan",
        "type": "secondary",
        "feed": "https://www.japantimes.co.jp/feed/business/",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Nikkei Asia – News",
        "region": "Japan",
        "type": "secondary",
        "feed": "https://asia.nikkei.com/rss/feed/nar",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "The Star Malaysia – Business",
        "region": "Malaysia",
        "type": "secondary",
        "feed": "https://www.thestar.com.my/rss/business",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Malay Mail – News",
        "region": "Malaysia",
        "type": "secondary",
        "feed": "https://www.malaymail.com/feed",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Channel NewsAsia – Business",
        "region": "Singapore",
        "type": "secondary",
        "feed": "https://www.channelnewsasia.com/rssfeeds/8395884",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Straits Times – Business",
        "region": "Singapore",
        "type": "secondary",
        "feed": "https://www.straitstimes.com/business/rss.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Korea Herald – Business",
        "region": "SouthKorea",
        "type": "secondary",
        "feed": "https://www.koreaherald.com/common/rss_xml.php?cat=biz",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Korea JoongAng Daily – News",
        "region": "SouthKorea",
        "type": "secondary",
        "feed": "https://koreajoongangdaily.joins.com/rss/feeds",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Bangkok Post – Business",
        "region": "Thailand",
        "type": "secondary",
        "feed": "https://www.bangkokpost.com/rss/data/business.xml",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "The Nation Thailand – News",
        "region": "Thailand",
        "type": "secondary",
        "feed": "https://www.nationthailand.com/rss",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — International Wire & Trade Press
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "Al Jazeera – Economy",
        "region": "International",
        "type": "secondary",
        "feed": "https://www.aljazeera.com/xml/rss/all.xml",
        "topics": ["supply_disruption", "partner_country"],
    },
    {
        "name": "Hellenic Shipping News – Oil & Energy",
        "region": "International",
        "type": "secondary",
        "feed": "https://www.hellenicshippingnews.com/category/oil-energy/feed/",
        "topics": ["shipments", "supply_disruption"],
    },
    {
        "name": "OilPrice.com – Energy News",
        "region": "International",
        "type": "secondary",
        "feed": "https://oilprice.com/rss/main",
        "topics": ["reserves_and_prices", "supply_disruption"],
    },
    {
        "name": "Energy Monitor – News",
        "region": "International",
        "type": "secondary",
        "feed": "https://www.energymonitor.ai/feed",
        "topics": ["policy_and_legislation", "supply_disruption"],
    },
    {
        "name": "Power Technology – Energy News",
        "region": "International",
        "type": "secondary",
        "feed": "https://www.power-technology.com/feed/",
        "topics": ["supply_disruption", "shipments"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — Australian & Regional Think Tanks
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "ASPI – The Strategist",
        "region": "Australia",
        "type": "secondary",
        # Australian Strategic Policy Institute — publishes specifically on
        # Australian energy security, Indo-Pacific supply chain risks and
        # fuel security policy. Directly relevant.
        "feed": "https://www.aspistrategist.org.au/feed/",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
    {
        "name": "Lowy Institute – The Interpreter",
        "region": "Australia",
        "type": "secondary",
        # Australian foreign policy think tank with strong Indo-Pacific focus.
        # Covers Australia's energy relationships with trading partners.
        "feed": "https://www.lowyinstitute.org/the-interpreter/feed",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — Regional News
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "South China Morning Post – Business",
        "region": "International",
        "type": "secondary",
        # Good coverage of regional energy developments affecting Singapore,
        # South Korea and Japan supply chains.
        "feed": "https://www.scmp.com/rss/91/feed",
        "topics": ["reserves_and_prices", "supply_disruption", "shipments", "trade_partner", "diesel"],
    },
]