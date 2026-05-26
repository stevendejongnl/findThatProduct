import json
import logging
import re
from urllib.parse import quote_plus, unquote, parse_qs, urlparse

import aiohttp

from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.browser import get_browser

logger = logging.getLogger(__name__)

BASE_URL = "https://html.duckduckgo.com/html/"
LINK_PATTERN = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<')

_NON_SHOP_DOMAINS = {
    "wikipedia.org", "reddit.com", "youtube.com", "facebook.com", "twitter.com",
    "instagram.com", "pinterest.com", "linkedin.com", "github.com",
    "gsmarena.com", "rtings.com", "tomsguide.com", "wired.com", "theverge.com",
    "techradar.com", "androidcentral.com", "phonearena.com", "notebookcheck.net",
    "androidworld.nl", "tweakers.net", "hardware.info", "nu.nl", "nos.nl",
    "google.com", "apple.com", "samsung.com", "microsoft.com",
    "blog.google", "android.com",
}

JSONLD_RE = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)
PRICE_META_RE = re.compile(r'content="([0-9]+(?:[.,][0-9]{1,2})?)"[^>]*itemprop="price"')
OG_PRICE_RE = re.compile(r'property="product:price:amount"[^>]*content="([0-9]+(?:[.,][0-9]{1,2})?)"')


def _extract_url(href: str) -> str | None:
    if href.startswith("//"):
        href = "https:" + href
    if not href.startswith("http"):
        return None
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        uddg = parse_qs(parsed.query).get("uddg", [None])[0]
        if not uddg:
            return None
        real = unquote(uddg)
        if "duckduckgo.com" in urlparse(real).netloc:
            return None
        return real
    return href


def _is_shop_url(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower().removeprefix("www.")
        return not any(netloc == d or netloc.endswith("." + d) for d in _NON_SHOP_DOMAINS)
    except Exception:
        return False


def _source_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return "web"


def _extract_price_from_html(html: str) -> float | None:
    for m in JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("@type") == "Product":
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price")
            if price is not None:
                try:
                    return float(str(price).replace(",", "."))
                except ValueError:
                    pass
    m = PRICE_META_RE.search(html)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    m = OG_PRICE_RE.search(html)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


async def _fetch_price(browser, url: str) -> float | None:
    context = await browser.new_context(locale="nl-NL")
    page = await context.new_page()
    try:
        await page.goto(url, timeout=12_000, wait_until="domcontentloaded")
        html = await page.content()
        return _extract_price_from_html(html)
    except Exception as e:
        logger.debug("DDG price fetch failed for %s: %s", url, e)
        return None
    finally:
        await page.close()
        await context.close()


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

        candidates: list[tuple[str, str]] = []
        for match in LINK_PATTERN.finditer(html):
            href, title = match.group(1), match.group(2).strip()
            link = _extract_url(href)
            if not link or not _is_shop_url(link):
                continue
            candidates.append((link, title))
            if len(candidates) >= 5:
                break

        if not candidates:
            return []

        import asyncio
        try:
            browser = get_browser()
            prices = await asyncio.gather(*[_fetch_price(browser, u) for u, _ in candidates])
        except RuntimeError:
            prices = [None] * len(candidates)

        results = []
        for (link, title), price in zip(candidates, prices):
            results.append(ProductResult(
                title=title,
                url=link,
                source="duckduckgo",
                price=price,
                currency="EUR",
            ))
        return results
