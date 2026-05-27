import pytest
from aioresponses import aioresponses
from src.infrastructure.duckduckgo import DuckDuckGoSource, _extract_url, _is_shop_url
from src.domain.search_query import SearchQuery, QueryType


EAN_QUERY = SearchQuery(raw="8710447308431", type=QueryType.EAN)
TEXT_QUERY = SearchQuery(raw="peanut butter", type=QueryType.TEXT)


def test_is_shop_url_allows_shops():
    assert _is_shop_url("https://www.verfwinkel.nl/product") is True
    assert _is_shop_url("https://www.bol.com/nl/nl/p/test/") is True


def test_is_shop_url_blocks_non_shops():
    assert _is_shop_url("https://www.wikipedia.org/wiki/Epoxy") is False
    assert _is_shop_url("https://www.gsmarena.com/google_pixel") is False
    assert _is_shop_url("https://blog.google/pixel") is False
    assert _is_shop_url("https://www.tweakers.net/pricewatch/") is False


def test_extract_url_ddg_ad_no_uddg_returns_none():
    href = "//duckduckgo.com/y.js?ad_domain=example.nl&ad_provider=bingv7"
    assert _extract_url(href) is None


def test_extract_url_ddg_ad_uddg_pointing_to_yjs_returns_none():
    from urllib.parse import quote
    inner = quote("https://duckduckgo.com/y.js?ad_domain=example.nl&ad_provider=bingv7aa", safe="")
    href = f"//duckduckgo.com/l/?uddg={inner}&rut=abc"
    assert _extract_url(href) is None


def test_extract_url_ddg_redirect():
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fshop.example.com%2Fproduct%2F1&rut=abc"
    assert _extract_url(href) == "https://shop.example.com/product/1"


def test_extract_url_direct():
    assert _extract_url("https://shop.example.com/product/1") == "https://shop.example.com/product/1"


def test_extract_url_invalid():
    assert _extract_url("//duckduckgo.com/l/?rut=abc") is None


@pytest.mark.vcr
async def test_text_query_returns_results(mocker):
    # Price fetching uses Playwright browser — stub both browser and fetch so
    # URL parsing and shop filtering logic is exercised with real DDG HTML.
    mocker.patch("src.infrastructure.duckduckgo.get_browser", return_value=object())
    mocker.patch("src.infrastructure.duckduckgo._fetch_price", return_value=4.99)
    source = DuckDuckGoSource()
    results = await source.search(TEXT_QUERY)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert all(r.source == "duckduckgo" for r in results)
    assert all(r.url.startswith("http") for r in results)
    assert all(r.price == 4.99 for r in results)


async def test_ean_query_searches_ean():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get(
            "https://html.duckduckgo.com/html/?q=8710447308431+kopen+prijs&kl=nl-nl",
            body="<html><body></body></html>",
            content_type="text/html",
        )
        results = await source.search(EAN_QUERY)
    assert isinstance(results, list)


async def test_http_error_returns_empty():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get("https://html.duckduckgo.com/html/?q=peanut+butter+kopen+prijs&kl=nl-nl", status=403)
        results = await source.search(TEXT_QUERY)
    assert results == []
