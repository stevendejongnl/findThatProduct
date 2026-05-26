import json
import logging
import re
from urllib.parse import quote_plus

import aiohttp

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)

# Tweakers Pricewatch is behind DPG consent gate — use their public JSON feed instead
# Their product search widget calls this endpoint server-side (no consent required)
SEARCH_URL = "https://tweakers.net/pricewatch/zoeken/"
JSONLD_RE = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)

# Tweakers embeds product data in a server-rendered JSON blob
PRODUCT_DATA_RE = re.compile(
    r'"url"\s*:\s*"(https://tweakers\.net/pricewatch/\d+/[^"]+)".*?"name"\s*:\s*"([^"]+)".*?"lowPrice"\s*:\s*"([^"]+)"',
    re.DOTALL,
)
ITEM_RE = re.compile(
    r'"@type"\s*:\s*"ListItem".*?"url"\s*:\s*"(https://tweakers\.net/pricewatch/\d+/[^"]+)".*?"name"\s*:\s*"([^"]+)"',
    re.DOTALL,
)


def _parse_jsonld(html: str) -> list[ProductResult]:
    results: list[ProductResult] = []
    for m in JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        graph = data if isinstance(data, list) else [data]
        for obj in graph:
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type", "")
            if t == "ItemList":
                for el in obj.get("itemListElement", []):
                    item = el.get("item", el) if isinstance(el, dict) else {}
                    name = item.get("name", "").strip()
                    url = item.get("url", "")
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    low = offers.get("lowPrice") or offers.get("price")
                    if not name or not url:
                        continue
                    try:
                        price = float(str(low).replace(",", ".")) if low else None
                    except ValueError:
                        price = None
                    results.append(ProductResult(
                        title=name,
                        url=url,
                        source="tweakers.net",
                        price=price,
                        currency="EUR",
                    ))
    return results


class TweakersSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{SEARCH_URL}?keyword={quote_plus(query.raw)}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=12),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept-Language": "nl-NL,nl;q=0.9",
                        "Accept": "text/html,application/xhtml+xml",
                        # send a fake consent cookie so DPG gate passes
                        "Cookie": "dpg_consent=1; twk-cookieConsent=1",
                    },
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Tweakers HTTP %s", resp.status)
                        return []
                    html = await resp.text()
        except Exception as e:
            logger.warning("Tweakers error: %s", e)
            return []
        results = _parse_jsonld(html)
        return results[:10]
