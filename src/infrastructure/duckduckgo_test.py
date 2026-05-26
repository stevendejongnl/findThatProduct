from aioresponses import aioresponses
from src.infrastructure.duckduckgo import DuckDuckGoSource
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


async def test_text_query_returns_links():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get(
            "https://html.duckduckgo.com/html/?q=peanut+butter",
            body=DDG_HTML,
            content_type="text/html",
        )
        results = await source.search(TEXT_QUERY)
    assert len(results) >= 1
    assert all(r.source == "duckduckgo" for r in results)
    assert all(r.url.startswith("http") for r in results)


async def test_ean_query_searches_ean():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get(
            "https://html.duckduckgo.com/html/?q=8710447308431",
            body=DDG_HTML,
            content_type="text/html",
        )
        results = await source.search(EAN_QUERY)
    assert isinstance(results, list)


async def test_http_error_returns_empty():
    source = DuckDuckGoSource()
    with aioresponses() as m:
        m.get("https://html.duckduckgo.com/html/?q=peanut+butter", status=403)
        results = await source.search(TEXT_QUERY)
    assert results == []
