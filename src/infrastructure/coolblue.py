import json
import logging
import re
from urllib.parse import quote_plus

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.browser import fetch_with_browser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coolblue.nl/zoeken"
JSONLD_RE = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)


def _parse(html: str) -> list[ProductResult]:
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
            results.append(ProductResult(
                title=name,
                url=url,
                source="coolblue.nl",
                price=float(price) if price is not None else None,
                currency=currency,
                image_url=image if isinstance(image, str) else None,
            ))
    return results


class CoolblueSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?query={quote_plus(query.raw)}"
        try:
            html = await fetch_with_browser(
                url,
                wait_for=".product-card",
                timeout=20_000,
            )
        except Exception as e:
            logger.warning("Coolblue error: %s", e)
            return []
        return _parse(html)[:10]
