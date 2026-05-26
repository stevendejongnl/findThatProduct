import json
import logging
import re
from urllib.parse import quote_plus

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.browser import get_browser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coolblue.nl/zoeken"
PRODUCT_LINK_RE = re.compile(r'href="(/product/(\d+)/([^"]+)\.html)"')


def _slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").title()


def _parse(html: str) -> list[ProductResult]:
    # Collect prices from dataLayer (ecomm_prodid → ecomm_pvalue)
    price_map: dict[str, float] = {}
    dl_m = re.search(r'"ecomm_prodid"\s*:\s*(\[[^\]]+\])', html)
    pv_m = re.search(r'"ecomm_pvalue"\s*:\s*(\[[^\]]+\])', html)
    if dl_m and pv_m:
        try:
            ids = json.loads(dl_m.group(1))
            vals = json.loads(pv_m.group(1))
            price_map = {str(pid): float(pval) for pid, pval in zip(ids, vals)}
        except (json.JSONDecodeError, ValueError):
            pass

    seen: set[str] = set()
    results: list[ProductResult] = []
    for m in PRODUCT_LINK_RE.finditer(html):
        path, prod_id, slug = m.group(1), m.group(2), m.group(3)
        url = f"https://www.coolblue.nl{path}"
        if url in seen:
            continue
        seen.add(url)
        title = _slug_to_title(slug)
        price = price_map.get(prod_id)
        results.append(ProductResult(
            title=title,
            url=url,
            source="coolblue.nl",
            price=price,
            currency="EUR",
        ))
    return results


class CoolblueSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?query={quote_plus(query.raw)}"
        browser = get_browser()
        context = await browser.new_context(
            locale="nl-NL",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        try:
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            await page.goto(url, timeout=25_000, wait_until="networkidle")
            html = await page.content()
        except Exception as e:
            logger.warning("Coolblue error: %s", e)
            return []
        finally:
            await page.close()
            await context.close()
        return _parse(html)[:10]
