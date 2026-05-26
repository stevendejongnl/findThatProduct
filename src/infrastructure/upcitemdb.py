import logging
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery, QueryType
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://api.upcitemdb.com/prod/trial/lookup"


class UPCitemdbSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        if query.type != QueryType.EAN:
            return []
        url = f"{BASE_URL}?upc={query.raw}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.warning("UPCitemdb error: %s", e)
            return []
        results = []
        for item in data.get("items", []):
            title = item.get("title")
            if not title:
                continue
            offers = item.get("offers", [])
            price: float | None = None
            offer_url = f"https://www.upcitemdb.com/upc/{query.raw}"
            if offers:
                try:
                    price = float(offers[0]["price"])
                    offer_url = offers[0].get("link", offer_url)
                except (KeyError, ValueError, TypeError):
                    pass
            images = item.get("images", [])
            results.append(
                ProductResult(
                    title=title,
                    url=offer_url,
                    source="upcitemdb",
                    price=price,
                    image_url=images[0] if images else None,
                    ean=query.raw,
                )
            )
        return results
