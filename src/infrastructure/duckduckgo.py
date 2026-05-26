import logging
import re
from urllib.parse import quote_plus
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://html.duckduckgo.com/html/"
LINK_PATTERN = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<')


class DuckDuckGoSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        search_term = quote_plus(query.raw)
        url = f"{BASE_URL}?q={search_term}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
        except Exception as e:
            logger.warning("DuckDuckGo error: %s", e)
            return []
        results = []
        for match in LINK_PATTERN.finditer(html):
            link, title = match.group(1), match.group(2).strip()
            if not link.startswith("http") or "duckduckgo" in link:
                continue
            results.append(
                ProductResult(
                    title=title,
                    url=link,
                    source="duckduckgo",
                )
            )
        return results[:10]
