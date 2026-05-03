"""
Scoring and ranking engine — Australian Diesel Fuel Security edition.

Four target areas:
  (a) Australian diesel situation — availability, price, trades/contracts
  (b) Supply chain changes for Australia's diesel trading partners
      (Japan, Malaysia, Singapore, South Korea, Taiwan, Thailand)
  (c) Public announcements by politicians or industry leaders from
      those countries or Australia regarding diesel and supply chains
  (d) Policy developments regarding diesel and related supply chains
      from Japan, Malaysia, Singapore, South Korea, Taiwan, Thailand

Scoring dimensions
──────────────────
1. Source type bonus      primary +20 | secondary +8
2. Topic bonus            specialist sources only (general media has topics=[])
3. Keyword matches        title + summary scanned against priority patterns
4. Negative patterns      suppress clear noise
5. Recency bonus          published today +10 | yesterday +5
6. Watchlist flag         upcoming events, reports, deadlines
7. Statement flag         named leader public statement detected
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from policy_monitor import config
from policy_monitor.collectors.models import PolicyItem

logger = logging.getLogger(__name__)


# ── Topic bonus — specialist sources only ─────────────────────────────────────
# General media sources have topics=[] and rely purely on keyword matching.
TOPIC_BONUS: dict[str, float] = {
    "reserves_and_prices":    15.0,
    "shipments":              10.0,
    "partner_country":         0.0,
    "supply_disruption":      12.0,
    "policy_and_legislation": 12.0,
}

# ── Priority keyword patterns ──────────────────────────────────────────────────
PRIORITY_PATTERNS: list[tuple[str, float]] = [

    # ── (a) Australian diesel situation: availability, price, contracts ────────
    (r"\bdiesel\b", 12.0),
    (r"\bliquid fuel\w*", 12.0),
    (r"\bfuel securit\w+", 12.0),
    (r"\bdiesel reserve\w*", 15.0),
    (r"\bfuel reserve\w*", 14.0),
    (r"\bstrategic (petroleum )?reserve\w*", 14.0),
    (r"\b90.day (reserve|obligation|stockholding)", 15.0),
    (r"\bminimum stockholding obligation|mso\b", 15.0),
    (r"\bfuel stockholding\w*", 14.0),
    (r"\bpetroleum reserve\w*", 13.0),
    (r"\bdiesel wholesale price\w*", 14.0),
    (r"\bterminal gate price\w*", 14.0),
    (r"\bstation outage\w*", 13.0),
    (r"\bpetrol station.{0,20}(empty|out of stock|no diesel)", 13.0),
    (r"\bfuel shortfall\w*", 14.0),
    (r"\bfuel ship\w*", 13.0),
    (r"\bfuel (contract|trade|deal|tender)\w*", 13.0),
    (r"\bdiesel (contract|trade|deal|import|purchase)\w*", 14.0),
    (r"\bfuel import\w*", 12.0),
    (r"\bdistillate\w*", 11.0),
    (r"\btanker arrival\w*", 13.0),
    (r"\bfuel import terminal\w*", 13.0),
    (r"\bbotany|geelong|fremantle|brisbane.{0,20}(fuel|terminal|tanker|diesel)", 12.0),
    (r"\biea obligation\w*", 14.0),
    (r"\baustralia.{0,30}90.day", 14.0),

    # ── (b) Supply chain changes — trading partners ───────────────────────────

    # Japan
    (r"\bjapan.{0,50}(diesel|fuel|oil|reserve|refin|supply chain|export|import)", 14.0),
    (r"\bjapan.{0,30}iea collective action", 15.0),
    (r"\bjapan.{0,30}(strategic reserve release|spr release)", 15.0),
    (r"\bjapan.{0,30}(diesel subsid|fuel subsid)", 13.0),
    (r"\bjapan.{0,30}(refiner|refinery|refining)", 13.0),
    (r"\bjapan.{0,30}(export ban|export cap|export restrict)", 14.0),
    (r"\banre\b|agency for natural resources and energy", 13.0),
    (r"\bjogmec\b", 13.0),
    (r"\bmeti.{0,20}(fuel|oil|energy|diesel|reserve)", 13.0),

    # Malaysia
    (r"\bmalaysia.{0,50}(diesel|fuel|oil|reserve|refin|supply chain|export|import)", 14.0),
    (r"\bpetronas\b", 13.0),
    (r"\bmalaysia.{0,30}(diesel subsid|fuel subsid|price control)", 14.0),
    (r"\bmalaysia.{0,30}(export ban|export cap|export restrict)", 14.0),
    (r"\bmalaysia.{0,30}(refiner|refinery|refining)", 13.0),

    # Singapore
    (r"\bsingapore.{0,50}(diesel|fuel|oil|reserve|refin|supply chain|export|import)", 14.0),
    (r"\bsingapore.{0,30}australia.{0,30}(fuel|oil|supply|agreement|deal|contract)", 15.0),
    (r"\bema singapore|energy market authority", 13.0),
    (r"\bsingapore.{0,30}(bunker|refin|trading hub|oil hub)", 13.0),

    # South Korea
    (r"\b(south )?korea.{0,50}(diesel|fuel|oil|reserve|refin|supply chain|export|import)", 14.0),
    (r"\bkorea.{0,30}iea collective action", 15.0),
    (r"\bkorea.{0,30}(strategic reserve release|spr release)", 15.0),
    (r"\bkorea.{0,30}(retail price cap|price control)", 14.0),
    (r"\bkorea.{0,30}(export ban|export cap|export restrict)", 14.0),
    (r"\bkorea.{0,30}(refiner|refinery|refining)", 13.0),
    (r"\bknoc\b|korea national oil", 13.0),

    # Taiwan
    (r"\btaiwan.{0,50}(diesel|fuel|oil|reserve|refin|supply chain|export|import)", 14.0),
    (r"\btaiwan.{0,30}(strategic reserve release|petroleum reserve|oil reserve)", 15.0),
    (r"\btaiwan.{0,30}(diesel subsid|fuel subsid|price control|price freeze)", 14.0),
    (r"\btaiwan.{0,30}(export ban|export cap|export restrict)", 14.0),
    (r"\btaiwan.{0,30}(refiner|refinery|refining)", 13.0),
    (r"\bcpc corporation\b.{0,40}(fuel|oil|diesel|petroleum|supply|price)", 14.0),
    (r"\bmoea\b.{0,30}(fuel|oil|diesel|petroleum|energy|reserve)", 13.0),
    (r"\benergy administration\b.{0,30}(taiwan|fuel|oil|diesel|petroleum)", 13.0),

    # Thailand
    (r"\bthailand.{0,50}(diesel|fuel|oil|reserve|refin|supply chain|export|import)", 14.0),
    (r"\bptt\b|ptt plc", 13.0),
    (r"\bthailand.{0,30}biodiesel blend", 14.0),
    (r"\bthailand.{0,30}(export ban|ban on export|export restrict)", 14.0),
    (r"\bthailand.{0,30}oil trader\w*", 13.0),
    (r"\bthailand.{0,30}(refiner|refinery|refining)", 13.0),

    # ── Geopolitical / shipping route signals ─────────────────────────────────
    (r"\bstrait of hormuz|hormuz", 13.0),
    (r"\bstrait of malacca|malacca strait", 13.0),
    (r"\bsouth china sea.{0,30}(shipping|supply|oil|fuel)", 12.0),
    (r"\bchoke point\w*", 11.0),
    (r"\bshipping disruption\w*", 12.0),
    (r"\bsupply disruption\w*", 12.0),
    (r"\bfuel supply (disruption|risk|securit)", 12.0),
    (r"\bport (congestion|disruption|closure)", 11.0),
    (r"\btanker\w*", 9.0),
    (r"\bbunkering\b", 9.0),
    (r"\brefiner\w+", 9.0),
    (r"\bcrude oil.{0,30}(price|supply|disruption|shortage)", 9.0),
    (r"\biran.{0,30}(oil|fuel|strait|sanction|ceasefire)", 11.0),
    (r"\bopec.{0,30}(cut|output|production|supply|decision)", 9.0),
    (r"\biea collective action", 14.0),

    # ── (c) & (d) Public statements and policy — Australian leaders ────────────
    (r"\bchris bowen\b.{0,50}(fuel|diesel|oil|petroleum|reserve|supply)", 14.0),
    (r"\bmadeleine king\b.{0,50}(fuel|diesel|oil|petroleum|reserve|supply)", 14.0),
    (r"\bdon farrell\b.{0,50}(fuel|diesel|oil|petroleum|reserve|supply)", 12.0),
    (r"\bjim chalmers\b.{0,50}(fuel|diesel|oil|petroleum|reserve|supply)", 11.0),
    (r"\banthony albanese.{0,50}(fuel|energy|singapore|oil|supply|diesel)", 15.0),
    (r"\balbanese.{0,30}singapore", 14.0),
    (r"\bpm.{0,20}(fuel|energy|diesel|supply|singapore)", 12.0),
    (r"\bminister (for|of) (energy|resources|fuel|climate|trade|finance|transport).{0,50}(fuel|diesel|oil|petroleum|reserve|supply)", 12.0),
    (r"\bdccew\b.{0,30}(fuel|diesel|oil|petroleum|reserve|supply)", 12.0),
    (r"\baemo\b.{0,30}(fuel|diesel|oil|reserve|supply)", 11.0),
    (r"\baccc.{0,20}(fuel|diesel|price|petrol)", 11.0),
    (r"\baustralia.{0,40}(fuel polic|fuel strateg|fuel plan|fuel secur)", 13.0),
    (r"\bappropriation.{0,30}fuel securit", 15.0),
    (r"\bfuel security response bill", 15.0),
    (r"\bparliament.{0,20}(fuel|energy|diesel)", 10.0),
    (r"\bsenate.{0,20}(fuel|energy|diesel)", 10.0),
    (r"\baustralia.{0,30}singapore.{0,30}(agree|deal|mou|contract).{0,30}fuel", 15.0),

    # ── (c) & (d) Public statements and policy — partner country leaders ───────
    # Japan
    (r"\bjapanese (prime minister|pm|minister|government|official).{0,50}(fuel|energy|oil|diesel|reserve|supply)", 14.0),
    (r"\bishiba\b.{0,40}(fuel|energy|oil|diesel)", 13.0),
    (r"\banre (director|chief|official|minister)", 13.0),

    # Malaysia
    (r"\banwar ibrahim\b.{0,50}(fuel|energy|oil|diesel|petronas|supply)", 14.0),
    (r"\bmalaysian (prime minister|pm|minister|government|official).{0,50}(fuel|energy|oil|diesel|supply)", 14.0),

    # Singapore
    (r"\blawrence wong\b.{0,50}(fuel|energy|oil|diesel|supply|australia)", 14.0),
    (r"\bsingapore (prime minister|pm|minister|government|official).{0,50}(fuel|energy|oil|diesel|supply)", 14.0),

    # South Korea
    (r"\byoon.{0,10}(fuel|energy|oil|diesel|reserve|supply)", 13.0),
    (r"\bkorean (prime minister|pm|minister|government|official).{0,50}(fuel|energy|oil|diesel|supply)", 14.0),

    # Taiwan
    (r"\btaiwan(?:ese)? (president|premier|minister|government|official).{0,50}(fuel|energy|oil|diesel|petroleum|supply)", 14.0),
    (r"\bmoea (minister|official|said|announced|released|confirmed|warned).{0,40}(fuel|energy|oil|diesel|petroleum|supply)", 13.0),

    # Thailand
    (r"\bpaetongtarn\b.{0,50}(fuel|energy|oil|diesel|ptt|supply)", 13.0),
    (r"\bthai (prime minister|pm|minister|government|official).{0,50}(fuel|energy|oil|diesel|supply)", 14.0),

    # ── Watchlist / forward-looking ───────────────────────────────────────────
    (r"\bupcoming (review|report|statement|decision|announcement)", 5.0),
    (r"\bpublic consultation|call for submissions?", 5.0),
    (r"\bdeadline|due date|closes?\b", 4.0),
    (r"\bscheduled|forthcoming|expected to (publish|announc|release)", 4.0),
    (r"\bcommittee hearing|senate hearing|parliamentary question", 5.0),
    (r"\bbudget (2026|2027).{0,20}(fuel|energy|reserve|diesel)", 6.0),
    (r"\boil market report|petroleum statistics", 5.0),
    (r"\biea.{0,20}(report|release|update|outlook)", 5.0),
]

# ── Negative keywords — suppress clear noise ───────────────────────────────────
NEGATIVE_PATTERNS: list[tuple[str, float]] = [
    # EV / renewables noise
    (r"\belectric (vehicle|truck|car|bus)\b", -10.0),
    (r"\bev charging\b", -10.0),
    (r"\bgreen (hydrogen|ammonia|energy)\b", -10.0),
    (r"\bused cooking oil\b|\bbiofuel boom\b|\brenewable diesel\b", -100.0),
    (r"\bsolar (panel|farm|power)\b", -8.0),
    (r"\bwind (farm|turbine|power)\b", -8.0),
    (r"\brenewable energy.{0,20}(replace|eliminat|substitut)", -8.0),
    # Crime / courts / unrelated domestic
    (r"\bcorrupt\w*|obeid|prosecution|criminal charge|murder|manslaughter", -20.0),
    (r"\bcourt (case|hearing|ruling|decision).{0,30}(?!fuel|oil|diesel|energy)", -10.0),
    (r"\bnitrous oxide|drowning|poison|bail breach", -20.0),
    # Media / entertainment / lifestyle
    (r"\bfashion|clothing|apparel|layered piece\w*|tactile", -20.0),
    (r"\bnasa\b.{0,30}(photo|image|picture|moon|space|artemis)", -20.0),
    (r"\bpodcast\b", -12.0),
    (r"\bbitcoin|crypto\w*|nft\b", -12.0),
    (r"\btourism|restaurant\w*|visitor\w*|hotel\w*", -12.0),
    (r"\bsports?\b.{0,20}(team|league|match|game|player|coach)", -15.0),
    # Finance noise unrelated to energy
    (r"\biron ore\b", -8.0),
    (r"\bstock market.{0,20}(?!oil|energy|fuel)", -5.0),
    (r"\breal estate|property market", -10.0),
    # Other unrelated industrial
    (r"\bfertiliz\w+", -8.0),
    (r"\bsemiconductor\b", -8.0),
    (r"\bhelium\b", -8.0),
    (r"\bchip (manufactur|shortage|supply).{0,20}(?!oil|fuel|diesel)", -8.0),
    # Fuel vouchers / retail promotions
    (r"\bfuel voucher|petrol station promot", -15.0),
    (r"\bpetrol price watch|weekly petrol price", -8.0),
]


# Hard relevance gate. Source/topic bonuses are useful only after the item proves
# it is about diesel, refined liquid fuels, or a near-term supply risk.
DIRECT_FUEL_PATTERNS: list[str] = [
    r"\bdiesel\b",
    r"\bpetrol\b",
    r"\bgasoline\b",
    r"\bgasoil\b",
    r"\bdistillate\w*\b",
    r"\bliquid fuel\w*\b",
    r"\bmiddle distillate\w*\b",
    r"\brefined (fuel|product|petroleum)\w*\b",
    r"\bpetroleum product\w*\b",
    r"\bfuel securit\w*\b",
    r"\bfuel reserve\w*\b",
    r"\bfuel stockholding\w*\b",
    r"\bminimum stockholding obligation|mso\b",
    r"\bterminal gate price\w*\b",
]

HARD_FUEL_PATTERNS: list[str] = [
    r"\bdiesel\b",
    r"\bpetrol\b",
    r"\bgasoline\b",
    r"\bgasoil\b",
    r"\bdistillate\w*\b",
    r"\bliquid fuel\w*\b",
    r"\bmiddle distillate\w*\b",
    r"\brefined (fuel|product|petroleum)\w*\b",
    r"\bpetroleum product\w*\b",
    r"\bfuel stockholding\w*\b",
    r"\bminimum stockholding obligation|mso\b",
    r"\bterminal gate price\w*\b",
    r"\bfuel import\w*\b",
]

CORE_DIESEL_PATTERNS: list[str] = [
    r"\bdiesel\b",
    r"\bpetrol\b",
    r"\bgasoline\b",
    r"\bgasoil\b",
    r"\bdistillate\w*\b",
    r"\bmiddle distillate\w*\b",
    r"\brefined (fuel|product|petroleum)\w*\b",
    r"\bpetroleum product\w*\b",
    r"\bterminal gate price\w*\b",
]

STRONG_MEDIA_FUEL_PATTERNS: list[str] = [
    r"\bdiesel\b",
    r"\bpetrol\b",
    r"\bgasoline\b",
    r"\bgasoil\b",
    r"\bdistillate\w*\b",
    r"\bmiddle distillate\w*\b",
    r"\bfuel securit\w*\b",
    r"\bfuel reserve\w*\b",
    r"\bfuel stockholding\w*\b",
    r"\bminimum stockholding obligation|mso\b",
    r"\bterminal gate price\w*\b",
    r"\bretail price\w*.{0,30}(fuel|petrol|diesel)\b",
    r"\b(fuel|diesel|petrol|gasoline).{0,30}(shortage|disruption|outage|rationing)\b",
    r"\b(refinery|refineries|refiner)\b.{0,40}(outage|fire|shutdown|strike|disruption|explosion|fuel|diesel|petrol|gasoline|oil)\b",
    r"\b(strait of hormuz|hormuz|strait of malacca|malacca strait).{0,80}(fuel|oil|diesel|tanker|shipping)\b",
]

CONTEXTUAL_RELEVANCE_PATTERNS: list[str] = [
    r"\baustralia\w*.{0,50}(fuel|diesel|petroleum|refin|import|stockholding|reserve|terminal gate)",
    r"\b(japan|malaysia|singapore|south korea|korea|taiwan|thailand).{0,50}(diesel|gasoil|fuel|petroleum|refin|export|import|reserve)",
    r"\b(refiner|refinery|refining|tanker|bunkering|port).{0,40}(diesel|fuel|oil|petroleum|gasoil)",
    r"\b(strait of hormuz|hormuz|strait of malacca|malacca strait|south china sea).{0,60}(diesel|fuel|oil|petroleum|tanker|shipping)",
    r"\b(oil|fuel|diesel|petroleum).{0,50}(export ban|export cap|export restrict|reserve release|supply disruption|shortage)",
]

STRATEGIC_OIL_PATTERNS: list[str] = [
    r"\bbrent crude oil\b.{0,50}(price|spot|futures|surge|rise|climb|fall)",
    r"\bcrude oil\b.{0,50}(price|spot|futures|surge|rise|climb|fall|supply)",
    r"\boil price\w*\b.{0,50}(surge|rise|climb|spike|shock|war|hormuz|iran)",
    r"\boil shock\w*\b",
    r"\bfuel cost\w*\b",
    r"\bfuel supply\b",
    r"\b(strait of hormuz|hormuz|strait of malacca|malacca strait).{0,80}(crisis|closure|reopen|blockade|shipping|route|supply|oil)",
    r"\b(japan|malaysia|singapore|south korea|korea|taiwan|thailand).{0,70}(crude oil|oil refiner|oil refinery|oil supply|oil import|oil export)",
    r"\b(bitumen|construction|logistics|trucking|freight).{0,80}(fuel|oil|diesel|hormuz|supply)",
]

LOW_SIGNAL_WITHOUT_FUEL_PATTERNS: list[str] = [
    r"\blng\b|\bliquefied natural gas\b|\bnatural gas\b|\bgas export\w*\b",
    r"\bnuclear\b|\bsmall modular reactor\w*\b|\bmicroreactor\w*\b",
    r"\belectricity\b|\bpower grid\b|\btransmission\b",
    r"\bsolar\b|\bwind\b|\brenewable\w*\b|\boffshore wind\b",
    r"\bhydrogen\b|\bammonia\b",
    r"\bai\b|\bartificial intelligence\b|\bsemiconductor\w*\b",
    r"\basx\b|\bstock\w*\b|\bshares?\b|\betf\w*\b|\bwall street\b|\bfinancial market\w*\b",
]

# ── Watchlist patterns ────────────────────────────────────────────────────────
WATCHLIST_PATTERNS: list[str] = [
    r"\bupcoming (review|report|statement|decision|announcement)",
    r"\bpublic consultation|call for submissions?",
    r"\bdeadline|due date|closes?\b",
    r"\bscheduled|forthcoming|expected to (publish|announc|release)",
    r"\bcommittee hearing|senate hearing|parliamentary question",
    r"\bbudget (2026|2027).{0,20}(fuel|energy|reserve|diesel)",
    r"\boil market report|petroleum statistics",
    r"\biea.{0,20}(report|release|update|outlook)",
    r"\baip.{0,20}(weekly|report|data|price)",
    r"\bbilateral (meeting|talks|summit).{0,40}(fuel|energy|oil|supply)",
    r"\btrade (meeting|talks|forum).{0,40}(australia|fuel|energy)",
    r"\bappropriation.{0,30}fuel securit",
    r"\biea collective action",
    r"\bexport (ban|cap|restrict).{0,20}(diesel|fuel|refined)",
    r"\bplanned (release|announc|statement|review).{0,30}(fuel|energy|diesel)",
    r"\bnext (week|month|quarter).{0,30}(fuel|energy|diesel|reserve)",
]

# ── Statement patterns — named leaders ────────────────────────────────────────
AU_POLITICAL_LEADERS: list[str] = [
    r"\banthony albanese\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
    r"\bchris bowen\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
    r"\bmadeleine king\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
    r"\bdon farrell\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
    r"\bjim chalmers\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
    r"\bpenny wong\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
    r"\bminister (for|of) (energy|resources|fuel|climate|trade|finance|transport).{0,50}(fuel|oil|diesel|petroleum|reserve|supply)",
    r"\bpm albanese\b.{0,50}(fuel|energy|oil|diesel|petroleum|reserve|supply)",
]

AU_PUBLIC_SERVICE: list[str] = [
    r"\bdccew\b.{0,30}(said|announced|released|confirmed|warned)",
    r"\baemo\b.{0,30}(said|announced|released|confirmed|warned)",
    r"\baccc\b.{0,30}(said|announced|released|confirmed|warned|found)",
    r"\babs\b.{0,30}(data|statistics|report|release).{0,20}(fuel|energy|oil|diesel)",
]

AU_INDUSTRY_LEADERS: list[str] = []

FOREIGN_LEADERS: list[str] = [
    r"\bjapanese (prime minister|pm|minister|official).{0,50}(fuel|energy|oil|diesel|reserve|supply)",
    r"\bishiba\b.{0,40}(fuel|energy|oil|diesel)",
    r"\banwar ibrahim\b.{0,50}(fuel|energy|oil|diesel|petronas|supply)",
    r"\bmalaysian (prime minister|pm|minister|official).{0,50}(fuel|energy|oil|diesel|supply)",
    r"\blawrence wong\b.{0,50}(fuel|energy|oil|diesel|supply|australia)",
    r"\bsingapore (prime minister|pm|minister|official).{0,50}(fuel|energy|oil|diesel|supply)",
    r"\byoon.{0,10}(fuel|energy|oil|diesel|reserve|supply)",
    r"\bkorean (prime minister|pm|minister|official).{0,50}(fuel|energy|oil|diesel|supply)",
    r"\btaiwan(?:ese)? (president|premier|minister|official).{0,50}(fuel|energy|oil|diesel|petroleum|supply)",
    r"\bmoea (minister|official|said|announced|released|confirmed|warned).{0,40}(fuel|energy|oil|diesel|petroleum|supply)",
    r"\bpaetongtarn\b.{0,50}(fuel|energy|oil|diesel|ptt|supply)",
    r"\bthai (prime minister|pm|minister|official).{0,50}(fuel|energy|oil|diesel|supply)",
]

STATEMENT_PATTERNS: list[str] = (
    AU_POLITICAL_LEADERS + AU_PUBLIC_SERVICE + AU_INDUSTRY_LEADERS + FOREIGN_LEADERS
)


def _compile_weighted(patterns: list[tuple[str, float]]) -> list[tuple[re.Pattern, float]]:
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_COMPILED_PRIORITY = _compile_weighted(PRIORITY_PATTERNS)
_COMPILED_NEGATIVE = _compile_weighted(NEGATIVE_PATTERNS)
_COMPILED_DIRECT_FUEL = _compile(DIRECT_FUEL_PATTERNS)
_COMPILED_HARD_FUEL = _compile(HARD_FUEL_PATTERNS)
_COMPILED_CORE_DIESEL = _compile(CORE_DIESEL_PATTERNS)
_COMPILED_STRONG_MEDIA_FUEL = _compile(STRONG_MEDIA_FUEL_PATTERNS)
_COMPILED_CONTEXTUAL_RELEVANCE = _compile(CONTEXTUAL_RELEVANCE_PATTERNS)
_COMPILED_STRATEGIC_OIL = _compile(STRATEGIC_OIL_PATTERNS)
_COMPILED_LOW_SIGNAL = _compile(LOW_SIGNAL_WITHOUT_FUEL_PATTERNS)
_COMPILED_WATCHLIST = _compile(WATCHLIST_PATTERNS)
_COMPILED_STATEMENT = _compile(STATEMENT_PATTERNS)

POLICY_OR_OFFICIAL_CONTEXT_PATTERNS: list[str] = [
    r"\bgovernment\b|\bministry\b|\bminister\b|\bsecretary\b|\btreasury\b|\bparliament\b|\bsenate\b",
    r"\bprime minister\b|\bpresident\b|\bpremier\b|\bpm\b",
    r"\bpolicy\b|\blegislation\b|\bregulat\w*\b|\blaw\b|\bbill\b|\bmandate\b",
    r"\bannounc\w*\b|\bsaid\b|\bconfirmed\b|\bwarned\b|\breleased\b|\bstatement\b",
    r"\b(diesel|gas|petrol|fuel).{0,20}(up|down|rise|fall|increase|decrease|higher|lower)\b",
    r"\b(up|down|higher|lower).{0,20}(diesel|gas|petrol|fuel)\b",
    r"\bsubsid\w*\b|\bprice cap\b|\bprice control\b|\bretail price\w*\b|\bfuel tax\w*\b",
    r"\breserve\w*\b|\bstockhold\w*\b|\bemergency\b|\bshortage\b|\bdisruption\b",
    r"\bexport (ban|cap|restrict)\b|\bimport restriction\b|\breserve release\b",
    r"\bstrait of hormuz\b|\bhormuz\b|\bstrait of malacca\b|\bmalacca strait\b",
]

_COMPILED_POLICY_OR_OFFICIAL = _compile(POLICY_OR_OFFICIAL_CONTEXT_PATTERNS)


def _direct_fuel_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_DIRECT_FUEL if pattern.search(text))


def _hard_fuel_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_HARD_FUEL if pattern.search(text))


def _core_diesel_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_CORE_DIESEL if pattern.search(text))


def _strong_media_fuel_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_STRONG_MEDIA_FUEL if pattern.search(text))


def _contextual_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_CONTEXTUAL_RELEVANCE if pattern.search(text))


def _strategic_oil_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_STRATEGIC_OIL if pattern.search(text))


def _policy_or_official_hits(text: str) -> int:
    return sum(1 for pattern in _COMPILED_POLICY_OR_OFFICIAL if pattern.search(text))


def _passes_relevance_gate(item: PolicyItem, text: str) -> bool:
    """
    Return True when the item is specific enough for the diesel briefing.

    Broad source feeds often publish adjacent energy, politics, finance, and
    shipping stories. They should not get into the briefing from source/topic
    points alone.
    """
    direct_hits = _direct_fuel_hits(text)
    hard_hits = _hard_fuel_hits(text)
    core_hits = _core_diesel_hits(text)
    strong_media_fuel_hits = _strong_media_fuel_hits(text)
    contextual_hits = _contextual_hits(text)
    strategic_hits = _strategic_oil_hits(text)
    policy_or_official_hits = _policy_or_official_hits(text)

    if any(pattern.search(text) for pattern in _COMPILED_LOW_SIGNAL):
        # A gas/LNG/electricity article with incidental "liquid fuels",
        # "fuel security", or "fuel imports" mentions should not lead a
        # diesel briefing unless it also names diesel/refined products.
        return core_hits > 0

    if direct_hits:
        return (
            item.source_type == "primary"
            or policy_or_official_hits > 0
            or strong_media_fuel_hits > 0
        )

    if strategic_hits:
        return item.source_type == "primary" or policy_or_official_hits > 0

    if item.source_type == "primary":
        return contextual_hits >= 1

    # Media/trade feeds should surface fuel policy, official announcements,
    # prices, reserves, emergency actions, or route disruptions - not ordinary
    # oil-company market moves.
    return contextual_hits >= 2 and policy_or_official_hits > 0


def score_item(item: PolicyItem) -> float:
    """Compute a relevance score for a single PolicyItem."""
    score = 0.0
    text = f"{item.title} {item.summary}"

    if not _passes_relevance_gate(item, text):
        return 0.0

    # 1. Source type bonus
    if item.source_type == "primary":
        score += 20.0
    else:
        score += 8.0

    # 2. Topic bonus — specialist sources only
    for topic in item.topics:
        score += TOPIC_BONUS.get(topic, 0.0)

    # 3. Positive keyword matches
    for pattern, weight in _COMPILED_PRIORITY:
        if pattern.search(text):
            score += weight

    # 4. Negative keyword adjustments
    for pattern, weight in _COMPILED_NEGATIVE:
        if pattern.search(text):
            score += weight  # weight is negative

    # 5. Recency bonus
    if item.published:
        age = datetime.now(timezone.utc) - item.published.astimezone(timezone.utc)
        if age < timedelta(hours=24):
            score += 10.0
        elif age < timedelta(hours=48):
            score += 5.0

    # 6. Watchlist flag
    for pattern in _COMPILED_WATCHLIST:
        if pattern.search(text):
            item.is_watchlist = True
            break

    # 7. Statement flag — named leader detected
    for pattern in _COMPILED_STATEMENT:
        if pattern.search(text):
            item.is_statement = True
            break

    return max(0.0, min(score, 100.0))


def rank_items(items: list[PolicyItem]) -> list[PolicyItem]:
    """Score every item and return relevant items sorted highest-first."""
    for item in items:
        item.score = score_item(item)

    ranked = sorted(
        [item for item in items if item.score >= config.MIN_RELEVANCE_SCORE],
        key=lambda x: x.score,
        reverse=True,
    )
    logger.info(
        "Ranked %d relevant items from %d collected; top score: %.1f",
        len(ranked), len(items),
        ranked[0].score if ranked else 0,
    )
    return ranked
