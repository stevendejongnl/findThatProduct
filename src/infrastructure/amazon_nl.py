import logging
import re
from urllib.parse import quote_plus

import aiohttp

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)

BASE_URL = "https://www.amazon.nl/s"

TITLE_RE = re.compile(r'<h2[^>]+aria-label="([^"]{5,300})"')
# a-offscreen span: "€\xa0251,99" or "€\xa029,99"
OFFSCREEN_PRICE_RE = re.compile(r'<span class="a-offscreen">[€$£]\xa0?([0-9]+)[,.]([0-9]{2})</span>')
SPONSORED_PREFIX = re.compile(r'^Gesponsorde advertentie\s*[-–]\s*', re.IGNORECASE)


def _parse(html: str) -> list[ProductResult]:
    results: list[ProductResult] = []
    seen: set[str] = set()

    blocks = re.split(r'(?=<div[^>]+data-component-type="s-search-result")', html)
    for block in blocks[1:]:
        asin_m = re.search(r'data-asin="([A-Z0-9]{10})"', block)
        if not asin_m:
            continue
        asin = asin_m.group(1)
        if asin in seen:
            continue
        seen.add(asin)

        t_m = TITLE_RE.search(block[:8000])
        if not t_m:
            continue
        title = SPONSORED_PREFIX.sub("", t_m.group(1)).strip()
        if not title:
            continue

        price: float | None = None
        p_m = OFFSCREEN_PRICE_RE.search(block[:8000])
        if p_m:
            try:
                price = float(f"{p_m.group(1)}.{p_m.group(2)}")
            except ValueError:
                pass

        results.append(ProductResult(
            title=title,
            url=f"https://www.amazon.nl/dp/{asin}",
            source="amazon.nl",
            price=price,
            currency="EUR",
        ))
        if len(results) >= 10:
            break

    return results


class AmazonNLSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?k={quote_plus(query.raw)}&language=nl_NL"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=12),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept-Language": "nl-NL,nl;q=0.9",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Amazon.nl HTTP %s", resp.status)
                        return []
                    html = await resp.text()
        except Exception as e:
            logger.warning("Amazon.nl error: %s", e)
            return []
        return _parse(html)
