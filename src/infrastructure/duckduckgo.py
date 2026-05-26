import logging
import re
from urllib.parse import quote_plus, unquote, parse_qs, urlparse
import aiohttp
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)
BASE_URL = "https://html.duckduckgo.com/html/"
LINK_PATTERN = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<')


def _extract_url(href: str) -> str | None:
    # DDG wraps links as //duckduckgo.com/l/?uddg=<encoded-url>&...
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        uddg = parse_qs(parsed.query).get("uddg", [None])[0]
        if uddg:
            return unquote(uddg)
        return None
    if href.startswith("http"):
        return href
    return None


class DuckDuckGoSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        search_term = quote_plus(query.raw)
        url = f"{BASE_URL}?q={search_term}&kl=nl-nl"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
                ) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
        except Exception as e:
            logger.warning("DuckDuckGo error: %s", e)
            return []
        results = []
        for match in LINK_PATTERN.finditer(html):
            href, title = match.group(1), match.group(2).strip()
            link = _extract_url(href)
            if not link:
                continue
            results.append(
                ProductResult(
                    title=title,
                    url=link,
                    source="duckduckgo",
                )
            )
        return results[:10]
