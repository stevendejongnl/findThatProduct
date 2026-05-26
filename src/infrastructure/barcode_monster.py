import logging
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery, QueryType
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://barcode.monster/api"


class BarcodeMonsterSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        if query.type != QueryType.EAN:
            return []
        url = f"{BASE_URL}/{query.raw}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.warning("BarcodeMonster error: %s", e)
            return []
        description = data.get("description")
        if not description:
            return []
        return [
            ProductResult(
                title=description,
                url=f"https://barcode.monster/{query.raw}",
                source="barcode_monster",
                ean=query.raw,
            )
        ]
