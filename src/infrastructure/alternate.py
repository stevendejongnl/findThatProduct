import json
import logging
import re
from urllib.parse import quote_plus

import aiohttp

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.browser import fetch_with_browser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alternate.nl/listing.xhtml"
JSONLD_RE = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)
# Fallback: data attributes in product tiles
PRICE_ATTR_RE = re.compile(r'data-price="([0-9.]+)"[^>]*data-name="([^"]+)"[^>]*data-url="([^"]+)"')


def _parse_jsonld(html: str) -> list[ProductResult]:
    results: list[ProductResult] = []
    for m in JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        items = []
        if isinstance(data, dict):
            t = data.get("@type", "")
            if t == "ItemList":
                items = [el.get("item", el) for el in data.get("itemListElement", [])]
            elif t == "Product":
                items = [data]
        for item in items:
            if item.get("@type") != "Product":
                continue
            name = item.get("name", "").strip()
            url = item.get("url", "")
            image = item.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price")
            currency = offers.get("priceCurrency", "EUR")
            if not name or not url:
                continue
            if not url.startswith("http"):
                url = "https://www.alternate.nl" + url
            results.append(ProductResult(
                title=name,
                url=url,
                source="alternate.nl",
                price=float(price) if price is not None else None,
                currency=currency,
                image_url=image if isinstance(image, str) else None,
            ))
    return results


class AlternateSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?q={quote_plus(query.raw)}"
        html = ""
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
                    if resp.status == 200:
                        html = await resp.text()
        except Exception as e:
            logger.warning("Alternate aiohttp error: %s", e)

        results = _parse_jsonld(html)
        if not results:
            # JS-rendered — fall back to playwright
            logger.debug("Alternate: no JSON-LD, trying Playwright")
            try:
                html = await fetch_with_browser(url, timeout=20_000)
                results = _parse_jsonld(html)
            except Exception as e:
                logger.warning("Alternate Playwright error: %s", e)

        return results[:10]
