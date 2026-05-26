import logging
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery, QueryType
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://world.openfoodfacts.org/api/v2/product"


class OpenFoodFactsSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        if query.type != QueryType.EAN:
            return []
        url = f"{BASE_URL}/{query.raw}.json"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.warning("OpenFoodFacts error: %s", e)
            return []
        if data.get("status") != 1:
            return []
        product = data.get("product", {})
        name = product.get("product_name") or product.get("generic_name")
        if not name:
            return []
        return [
            ProductResult(
                title=name,
                url=product.get("url", url),
                source="open_food_facts",
                image_url=product.get("image_url"),
                ean=query.raw,
            )
        ]
