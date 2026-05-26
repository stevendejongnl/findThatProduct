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
    # Pre-collect all h2 positions so we can find the nearest one before each price
    h2_matches = list(TITLE_RE.finditer(html))
    results = []
    seen_urls: set[str] = set()
    for price_match in PRICE_RE.finditer(html):
        euros, cents = price_match.group(1), price_match.group(2)
        price = float(f"{euros}.{cents}")
        pos = price_match.start()
        segment_before = html[max(0, pos - 4000) : pos]
        links = list(LINK_RE.finditer(segment_before))
        if not links:
            continue
        path = links[-1].group(1)
        url = f"https://www.bol.com{path}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        # Nearest h2 before the price position
        preceding_h2 = [m for m in h2_matches if m.start() < pos]
        title = (
            preceding_h2[-1].group(1).strip()
            if preceding_h2
            else path.split("/")[-2].replace("-", " ").title()
        )
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
