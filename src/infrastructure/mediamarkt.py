import json
import logging
import re
from urllib.parse import quote_plus
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://www.mediamarkt.nl/nl/search.html"

# MediaMarkt embeds JSON-LD ItemList on search pages
JSONLD_RE = re.compile(r'<script type="application/ld\+json">(\{[^<]*"@type"\s*:\s*"ItemList"[^<]+)</script>')


def _parse_products(html: str) -> list[ProductResult]:
    m = JSONLD_RE.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    results = []
    for item in data.get("itemListElement", []):
        product = item.get("item", {})
        name = product.get("name", "").strip()
        url = product.get("url", "")
        offers = product.get("offers", {})
        price = offers.get("price")
        currency = offers.get("priceCurrency", "EUR")
        image = product.get("image")
        if not name or not url:
            continue
        results.append(
            ProductResult(
                title=name,
                url=url,
                source="mediamarkt.nl",
                price=float(price) if price is not None else None,
                currency=currency,
                image_url=image,
            )
        )
    return results


class MediaMarktSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?query={quote_plus(query.raw)}"
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
            logger.warning("MediaMarkt error: %s", e)
            return []
        return _parse_products(html)[:10]
