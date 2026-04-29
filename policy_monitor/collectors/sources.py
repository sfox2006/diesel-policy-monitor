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
  partner_country        – developments in Japan/Malaysia/Singapore/Korea/Taiwan/Thailand
                           affecting what Australia can import
  policy_and_legislation – bills, ministerial statements, IEA obligations,
                           DCCEEW/PM releases
  supply_disruption      – refinery outages, route disruptions, geopolitical
                           risk flags; weighted higher for urgency alerting

Regions used:
  Australia, Japan, Malaysia, Singapore, SouthKorea, Taiwan, Thailand, International

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
    {
        "name": "Minister Bowen – Energy Media Releases",
        "region": "Australia",
        "type": "primary",
        "scrape_url": "https://minister.dcceew.gov.au/bowen/media-releases",
        "scrape_cfg": {"list_selector": ".views-row", "title": "h2", "link": "a"},
        "topics": ["policy_and_legislation", "reserves_and_prices", "supply_disruption"],
    },
    {
        "name": "Minister Bowen – Energy Transcripts",
        "region": "Australia",
        "type": "primary",
        "scrape_url": "https://minister.dcceew.gov.au/bowen/transcripts",
        "scrape_cfg": {"list_selector": ".views-row", "title": "h2", "link": "a"},
        "topics": ["policy_and_legislation", "reserves_and_prices", "supply_disruption"],
    },
    {
        "name": "Industry, Science and Resources Ministers – Media Releases",
        "region": "Australia",
        "type": "primary",
        "scrape_url": "https://www.minister.industry.gov.au/ministers/media-releases",
        "scrape_cfg": {"list_selector": ".views-row", "title": "h2", "link": "a"},
        "topics": ["policy_and_legislation", "partner_country", "supply_disruption"],
    },
    {
        "name": "Minister King – Resources Media Releases",
        "region": "Australia",
        "type": "primary",
        "scrape_url": "https://www.minister.industry.gov.au/ministers/king/media-releases",
        "scrape_cfg": {"list_selector": ".views-row", "title": "h2", "link": "a"},
        "topics": ["policy_and_legislation", "partner_country", "supply_disruption"],
    },
    {
        "name": "Minister Ayres – Industry and Manufacturing Media Releases",
        "region": "Australia",
        "type": "primary",
        "scrape_url": "https://www.minister.industry.gov.au/ministers/timayres/media-releases",
        "scrape_cfg": {"list_selector": ".views-row", "title": "h2", "link": "a"},
        "topics": ["policy_and_legislation", "partner_country", "supply_disruption"],
    },
    {
        "name": "Minister Catherine King – Transport and Infrastructure Media Releases",
        "region": "Australia",
        "type": "primary",
        "scrape_url": "https://minister.infrastructure.gov.au/c-king/media-release",
        "scrape_cfg": {"list_selector": ".views-row", "title": "a", "link": "a"},
        "topics": ["policy_and_legislation", "shipments", "supply_disruption"],
    },
    {
        "name": "Dan Tehan – Opposition Energy Media Releases",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://dantehan.com.au/category/media-releases/",
        "scrape_cfg": {"list_selector": ".dt-posts-reel-main", "title": "a", "link": "a"},
        "topics": [],
    },
    {
        "name": "Liberal Party of Australia – Opposition News and Releases",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.liberal.org.au/articles",
        "scrape_cfg": {"list_selector": "article", "title": "a", "link": "a"},
        "topics": [],
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
        "topics": [],
    },
    {
        "name": "National Farmers Federation – News",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.nff.org.au/feed/",
        "topics": [],
    },
    {
        "name": "Minerals Council of Australia – News",
        "region": "Australia",
        "type": "primary",
        "feed": "https://www.minerals.org.au/feed/",
        "topics": [],
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
        "topics": ["partner_country"],
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
    {
        "name": "Japan Prime Minister's Office - Latest Information",
        "region": "Japan",
        "type": "primary",
        "feed": "https://japan.kantei.go.jp/index-e2.rdf",
        "topics": ["partner_country", "policy_and_legislation", "supply_disruption"],
    },
    {
        "name": "Japan Ministry of Finance - News Release",
        "region": "Japan",
        "type": "primary",
        "feed": "https://www.mof.go.jp/english/news.rss",
        "topics": ["partner_country", "policy_and_legislation"],
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
    {
        "name": "Malaysia Ministry of Finance - Press Releases",
        "region": "Malaysia",
        "type": "primary",
        "scrape_url": "https://www.mof.gov.my/portal/en/news/press-release",
        "scrape_cfg": {"list_selector": "li.list-group-item", "title": ".item-info a", "link": ".item-info a"},
        "topics": ["policy_and_legislation", "reserves_and_prices"],
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
    {
        "name": "Singapore Business Times - Top Stories",
        "region": "Singapore",
        "type": "secondary",
        "feed": "https://www.businesstimes.com.sg/rss/top-stories",
        "topics": [],
    },
    {
        "name": "Singapore Business Times - Companies and Markets",
        "region": "Singapore",
        "type": "secondary",
        "feed": "https://www.businesstimes.com.sg/rss/companies-markets",
        "topics": [],
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
    {
        "name": "Yonhap News Agency - All News",
        "region": "SouthKorea",
        "type": "secondary",
        "feed": "https://en.yna.co.kr/RSS/news.xml",
        "topics": [],
    },
    {
        "name": "KBS World - News",
        "region": "SouthKorea",
        "type": "secondary",
        "feed": "https://world.kbs.co.kr/rss/rss_news.htm?lang=e",
        "topics": [],
    },

    # PRIMARY - Taiwan

    {
        "name": "Taiwan Ministry of Economic Affairs - What's New",
        "region": "Taiwan",
        "type": "primary",
        "scrape_url": "https://www.moea.gov.tw/MNS/english/news/News.aspx?kind=6&menu_id=176",
        "scrape_cfg": {"list_selector": "tr", "title": "a[href*='news_id']", "link": "a[href*='news_id']"},
        "topics": ["partner_country", "policy_and_legislation"],
    },
    {
        "name": "Taiwan Energy Administration - What's New",
        "region": "Taiwan",
        "type": "primary",
        "scrape_url": "https://www.moeaea.gov.tw/ECW/english/news/News.aspx?kind=6&menu_id=958",
        "scrape_cfg": {"list_selector": "tr", "title": "a[href*='news_id']", "link": "a[href*='news_id']"},
        "topics": ["reserves_and_prices", "policy_and_legislation", "supply_disruption"],
    },
    {
        "name": "CPC Corporation Taiwan - News and Events",
        "region": "Taiwan",
        "type": "primary",
        "scrape_url": "https://www.cpc.com.tw/en/News.aspx?n=2705&sms=8994",
        "scrape_cfg": {"list_selector": "tr", "title": "a[href*='News_Content']", "link": "a[href*='News_Content']"},
        "topics": ["reserves_and_prices", "shipments", "supply_disruption"],
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
        "name": "ABC News – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.abc.net.au/news/feed/51120/rss.xml",
        "topics": [],
    },
    {
        "name": "ABC News – Science & Environment",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.abc.net.au/news/feed/52278/rss.xml",
        "topics": [],
    },
    {
        "name": "ABC News – Politics",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.abc.net.au/news/feed/51892/rss.xml",
        "topics": [],
    },
    {
        "name": "Sydney Morning Herald – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.smh.com.au/rss/business.xml",
        "topics": [],
    },
    {
        "name": "Sydney Morning Herald – National",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.smh.com.au/rss/national.xml",
        "topics": [],
    },
    {
        "name": "The Age – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.theage.com.au/rss/business.xml",
        "topics": [],
    },
    {
        "name": "The Guardian Australia – Business",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.theguardian.com/australia-news/business/rss",
        "topics": [],
    },
    {
        "name": "The Guardian Australia – Environment",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.theguardian.com/australia-news/environment/rss",
        "topics": [],
    },
    {
        "name": "RenewEconomy – Energy News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://reneweconomy.com.au/feed/",
        "topics": [],
    },
    {
        "name": "Sky News Australia",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.skynews.com.au/rss.xml",
        "topics": [],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — Regional / Partner Country Media
    # ══════════════════════════════════════════════════════════════════════════

    {
        "name": "Japan Times – Business",
        "region": "Japan",
        "type": "secondary",
        "feed": "https://www.japantimes.co.jp/feed/business/",
        "topics": [],
    },
    {
        "name": "Nikkei Asia – News",
        "region": "Japan",
        "type": "secondary",
        "feed": "https://asia.nikkei.com/rss/feed/nar",
        "topics": [],
    },
    {
        "name": "The Star Malaysia – Business",
        "region": "Malaysia",
        "type": "secondary",
        "feed": "https://www.thestar.com.my/rss/business",
        "topics": [],
    },
    {
        "name": "Malay Mail – News",
        "region": "Malaysia",
        "type": "secondary",
        "feed": "https://www.malaymail.com/feed/rss/malaysia",
        "topics": [],
    },
    {
        "name": "Malay Mail - Money",
        "region": "Malaysia",
        "type": "secondary",
        "feed": "https://www.malaymail.com/feed/rss/money",
        "topics": [],
    },
    {
        "name": "Free Malaysia Today - Business",
        "region": "Malaysia",
        "type": "secondary",
        "feed": "https://www.freemalaysiatoday.com/category/business/feed/",
        "topics": [],
    },
    {
        "name": "Channel NewsAsia – Business",
        "region": "Singapore",
        "type": "secondary",
        "feed": "https://www.channelnewsasia.com/rssfeeds/8395884",
        "topics": [],
    },
    {
        "name": "Straits Times – Business",
        "region": "Singapore",
        "type": "secondary",
        "feed": "https://www.straitstimes.com/business/rss.xml",
        "topics": [],
    },
    {
        "name": "Korea Herald – Business",
        "region": "SouthKorea",
        "type": "secondary",
        "feed": "https://www.koreaherald.com/common/rss_xml.php?cat=biz",
        "topics": [],
    },
    {
        "name": "Korea JoongAng Daily – News",
        "region": "SouthKorea",
        "type": "secondary",
        "feed": "https://koreajoongangdaily.joins.com/rss/feeds",
        "topics": [],
    },
    {
        "name": "Focus Taiwan - Business",
        "region": "Taiwan",
        "type": "secondary",
        "scrape_url": "https://focustaiwan.tw/business",
        "scrape_cfg": {"list_selector": "a[href^='/business/']", "title": "a", "link": "a"},
        "topics": [],
    },
    {
        "name": "Taipei Times - News",
        "region": "Taiwan",
        "type": "secondary",
        "feed": "https://www.taipeitimes.com/xml/index.rss",
        "topics": [],
    },
    {
        "name": "Bangkok Post – Business",
        "region": "Thailand",
        "type": "secondary",
        "feed": "https://www.bangkokpost.com/rss/data/business.xml",
        "topics": [],
    },
    {
        "name": "The Nation Thailand – News",
        "region": "Thailand",
        "type": "secondary",
        "feed": "https://www.nationthailand.com/rss",
        "topics": [],
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
        "topics": [],
    },
    {
        "name": "Lowy Institute – The Interpreter",
        "region": "Australia",
        "type": "secondary",
        # Australian foreign policy think tank with strong Indo-Pacific focus.
        # Covers Australia's energy relationships with trading partners.
        "feed": "https://www.lowyinstitute.org/the-interpreter/feed",
        "topics": [],
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
        "topics": [],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECONDARY — Australian Unions & Industry Bodies
    # All have topics=[] — only surface articles matching diesel/fuel keywords
    # ══════════════════════════════════════════════════════════════════════════

    # ── Services ──────────────────────────────────────────────────────────────
    {
        "name": "Australian Services Union – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.asu.asn.au/news",
        "scrape_cfg": {"list_selector": "div.news-item", "title": "h3", "link": "a"},
        "topics": [],
    },
    {
        "name": "United Workers Union – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://unitedworkers.org.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Shop, Distributive and Allied Employees Association – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.sda.com.au/news/",
        "scrape_cfg": {"list_selector": "div.news-item", "title": "h3", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Industry Group – News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.aigroup.com.au/news/rss/",
        "topics": [],
    },
    {
        "name": "Business Council of Australia – Media Releases",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.bca.com.au/media/media_releases/",
        "scrape_cfg": {"list_selector": "div.media-release", "title": "h3", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Chamber of Commerce and Industry – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.acci.com.au/news-and-media/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Retailers Association – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.retail.org.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Mining ────────────────────────────────────────────────────────────────
    {
        "name": "Mining and Energy Union – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://meu.org.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Workers Union – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.awu.net.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Minerals Council of Australia – News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.minerals.org.au/feed/",
        "topics": [],
    },
    {
        "name": "Chamber of Minerals and Energy WA – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.cmewa.com/news-and-resources/media-releases/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Agriculture ───────────────────────────────────────────────────────────
    {
        "name": "National Farmers Federation – News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://nff.org.au/feed/",
        "topics": [],
    },
    {
        "name": "GrainGrowers – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.graingrowers.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Meat and Livestock Australia – News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.mla.com.au/news-and-events/news/rss/",
        "topics": [],
    },
    {
        "name": "Dairy Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.dairyaustralia.com.au/news-and-updates",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Cotton Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://cottonaustralia.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Construction ──────────────────────────────────────────────────────────
    {
        "name": "Master Builders Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.masterbuilders.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Housing Industry Association – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://hia.com.au/about/media-centre/media-releases",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Constructors Association – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.constructors.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Transport ─────────────────────────────────────────────────────────────
    {
        "name": "Transport Workers Union – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.twu.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Maritime Union of Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.mua.org.au/news",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Trucking Association – News",
        "region": "Australia",
        "type": "secondary",
        "feed": "https://www.truck.net.au/feed",
        "topics": [],
    },
    {
        "name": "Australian Logistics Council – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://austlogistics.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Shipping Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://shippingaustralia.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Gas / Energy ──────────────────────────────────────────────────────────
    {
        "name": "Australian Energy Market Operator – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://aemo.com.au/en/news-centre/media-releases",
        "scrape_cfg": {"list_selector": "div.media-release-item", "title": "h3", "link": "a"},
        "topics": [],
    },
    {
        "name": "Energy Networks Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.energynetworks.com.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Australian Pipelines and Gas Association – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.apga.org.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
    {
        "name": "Clean Energy Council – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.cleanenergycouncil.org.au/news",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Government / Public Sector ────────────────────────────────────────────
    {
        "name": "Institute of Public Administration Australia – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.ipaa.org.au/news/",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },

    # ── Manufacturing ─────────────────────────────────────────────────────────
    {
        "name": "Australian Manufacturing Workers Union – News",
        "region": "Australia",
        "type": "secondary",
        "scrape_url": "https://www.amwu.org.au/news",
        "scrape_cfg": {"list_selector": "article", "title": "h2", "link": "a"},
        "topics": [],
    },
]
