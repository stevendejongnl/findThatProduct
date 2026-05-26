from aioresponses import aioresponses
from src.infrastructure.duckduckgo import DuckDuckGoSource, _extract_url
from src.domain.search_query import SearchQuery, QueryType


EAN_QUERY = SearchQuery(raw="8710447308431", type=QueryType.EAN)
TEXT_QUERY = SearchQuery(raw="peanut butter", type=QueryType.TEXT)

DDG_HTML = """
<html><body>
<div class="result">
  <a class="result__a" href="https://shop.example.com/product/1">Peanut Butter 500g</a>
</div>
<div class="result">
  <a class="result__a" href="https://another.com/product/2">Peanut Butter Organic</a>
</div>
</body></html>
"""

# Real DDG wraps links via //duckduckgo.com/l/?uddg=<encoded>
DDG_HTML_REDIRECT = """
<html><body>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fshop.example.com%2Fproduct%2F1&amp;rut=abc">Peanut Butter 500g</a>
</div>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fanother.com%2Fproduct%2F2&amp;rut=def">Peanut Butter Organic</a>
</div>
</body></html>
"""


def test_extract_url_ddg_redirect():
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fshop.example.com%2Fproduct%2F1&rut=abc"
    assert _extract_url(href) == "https://shop.example.com/product/1"


def test_extract_url_direct():
    assert _extract_url("https://shop.example.com/product/1") == "https://shop.example.com/product/1"


def test_extract_url_invalid():
    assert _extract_url("//duckduckgo.com/l/?rut=abc") is None


async def test_text_query_returns_links():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get(
            "https://html.duckduckgo.com/html/?q=peanut+butter&kl=nl-nl",
            body=DDG_HTML,
            content_type="text/html",
        )
        results = await source.search(TEXT_QUERY)
    assert len(results) >= 1
    assert all(r.source == "duckduckgo" for r in results)
    assert all(r.url.startswith("http") for r in results)


async def test_text_query_ddg_redirect_format():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get(
            "https://html.duckduckgo.com/html/?q=peanut+butter&kl=nl-nl",
            body=DDG_HTML_REDIRECT,
            content_type="text/html",
        )
        results = await source.search(TEXT_QUERY)
    assert len(results) == 2
    assert results[0].url == "https://shop.example.com/product/1"
    assert results[1].url == "https://another.com/product/2"
    assert all(r.url.startswith("http") for r in results)


async def test_ean_query_searches_ean():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get(
            "https://html.duckduckgo.com/html/?q=8710447308431&kl=nl-nl",
            body=DDG_HTML,
            content_type="text/html",
        )
        results = await source.search(EAN_QUERY)
    assert isinstance(results, list)


async def test_http_error_returns_empty():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get("https://html.duckduckgo.com/html/?q=peanut+butter&kl=nl-nl", status=403)
        results = await source.search(TEXT_QUERY)
    assert results == []
