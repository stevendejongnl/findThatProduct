import logging
import re
from urllib.parse import quote_plus
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://www.bol.com/nl/nl/s/"

# aria-label: "De prijs van dit productvariant is '409' euro en '00' cent"
PRICE_RE = re.compile(
    r"aria-label=\"De prijs van dit productvariant is &#x27;(\d+)&#x27; euro en &#x27;(\d+)&#x27; cent\""
)
LINK_RE = re.compile(r'href="(/nl/nl/p/([^/\"]+)/\d+/)"')
TITLE_RE = re.compile(r"<h2[^>]*>([^<]{5,120})</h2>")


def _parse_products(html: str) -> list[ProductResult]:
    results = []
    for price_match in PRICE_RE.finditer(html):
        euros, cents = price_match.group(1), price_match.group(2)
        price = float(f"{euros}.{cents}")
        segment_before = html[max(0, price_match.start() - 4000) : price_match.start()]
        links = list(LINK_RE.finditer(segment_before))
        if not links:
            continue
        path = links[-1].group(1)
        url = f"https://www.bol.com{path}"
        # title is in <h2> inside the anchor that follows the link href
        link_end = links[-1].end()
        segment_after = segment_before[link_end:] + html[price_match.start() : price_match.start() + 200]
        title_match = TITLE_RE.search(segment_before[links[-1].start() :])
        title = title_match.group(1).strip() if title_match else path.split("/")[-2].replace("-", " ").title()
        results.append(
            ProductResult(
                title=title,
                url=url,
                source="bol.com",
                price=price,
                currency="EUR",
            )
        )
    return results


class BolSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        params = f"?searchtext={quote_plus(query.raw)}"
        url = BASE_URL + params
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept-Language": "nl-NL,nl;q=0.9",
                    },
                ) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
        except Exception as e:
            logger.warning("bol.com error: %s", e)
            return []
        return _parse_products(html)[:10]
