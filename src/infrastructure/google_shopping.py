import logging
import re
from urllib.parse import quote_plus

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.browser import get_browser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.google.com/search"
PRICE_RE = re.compile(r"(\d+)[,.](\d{2})")

_EXTRACT_JS = """
() => {
    const out = [];
    const seen = new Set();
    for (const card of document.querySelectorAll("div.mnr-c")) {
        const link = card.querySelector("a[data-merchant-id]");
        if (!link) continue;
        const url = link.href;
        if (!url || seen.has(url) || url.includes("google.com")) continue;
        seen.add(url);

        let title = "";
        for (const el of card.querySelectorAll("div")) {
            const t = (el.innerText || "").trim();
            if (!el.className && t.length > 10 && el.children.length === 0) {
                title = t; break;
            }
        }

        const priceEl = card.querySelector(".VbBaOe");
        const priceRaw = priceEl ? priceEl.innerText.trim() : "";

        const shopEl = card.querySelector(".UsGWMe");
        const shop = shopEl ? shopEl.innerText.trim() : "";

        if (title && priceRaw) out.push({ title, priceRaw, shop, url });
    }
    return out;
}
"""


def _parse_price(raw: str) -> float | None:
    m = PRICE_RE.search(raw.replace("\xa0", ""))
    if not m:
        return None
    try:
        return float(f"{m.group(1)}.{m.group(2)}")
    except ValueError:
        return None


class GoogleShoppingSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        url = f"{BASE_URL}?q={quote_plus(query.raw)}&gl=nl&hl=nl&udm=28"
        browser = get_browser()
        context = await browser.new_context(
            locale="nl-NL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        try:
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            await page.goto(url, timeout=25_000, wait_until="networkidle")

            # dismiss consent gate if present
            try:
                await page.click('button:has-text("Alles accepteren")', timeout=3_000)
                await page.wait_for_timeout(1_500)
            except Exception:
                pass

            raw_items: list[dict] = await page.evaluate(_EXTRACT_JS)
        except Exception as e:
            logger.warning("Google Shopping error: %s", e)
            return []
        finally:
            await page.close()
            await context.close()

        results: list[ProductResult] = []
        seen_urls: set[str] = set()
        for item in raw_items:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            price = _parse_price(item.get("priceRaw", ""))
            shop = item.get("shop") or "google shopping"
            results.append(ProductResult(
                title=item["title"],
                url=url,
                source=shop.lower(),
                price=price,
                currency="EUR",
            ))

        logger.info("Google Shopping: %d results for %r", len(results), query.raw)
        return results[:15]
