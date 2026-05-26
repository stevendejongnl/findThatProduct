import logging
import re
from urllib.parse import quote_plus

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.browser import get_browser

logger = logging.getLogger(__name__)

BASE_URL = "https://tweakers.net/pricewatch/zoeken/"

# Tweakers product cards: /pricewatch/<id>/<slug>/
PRODUCT_RE = re.compile(r'href="(https://tweakers\.net/pricewatch/\d+/[^/"]+/)"[^>]*>([^<]{3,120})<')
PRICE_RE = re.compile(r'[€€]\s*(\d+[\.,]\d{2})')


def _parse_price(text: str) -> float | None:
    m = PRICE_RE.search(text)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def _parse(html: str) -> list[ProductResult]:
    seen: set[str] = set()
    results: list[ProductResult] = []
    for m in PRODUCT_RE.finditer(html):
        url, title = m.group(1), m.group(2).strip()
        if url in seen:
            continue
        seen.add(url)
        # Extract price from surrounding context
        start = max(0, m.start() - 500)
        snippet = html[start: m.end() + 500]
        price = _parse_price(snippet)
        results.append(ProductResult(
            title=title,
            url=url,
            source="tweakers.net",
            price=price,
            currency="EUR",
        ))
    return results


class TweakersSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?keyword={quote_plus(query.raw)}"
        browser = get_browser()
        context = await browser.new_context(locale="nl-NL")
        page = await context.new_page()
        try:
            await page.goto(url, timeout=20_000, wait_until="domcontentloaded")
            # wait for product list
            try:
                await page.wait_for_selector(".listing-search-results", timeout=8_000)
            except Exception:
                pass
            html = await page.content()
        except Exception as e:
            logger.warning("Tweakers error: %s", e)
            return []
        finally:
            await page.close()
            await context.close()
        return _parse(html)[:10]
