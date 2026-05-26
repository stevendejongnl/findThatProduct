from aioresponses import aioresponses
from src.infrastructure.bol import BolSource, _parse_products
from src.domain.search_query import SearchQuery, QueryType

TEXT_QUERY = SearchQuery(raw="Google Pixel", type=QueryType.TEXT)
EAN_QUERY = SearchQuery(raw="8710447308431", type=QueryType.EAN)

BOL_HTML = """
<html><body>
<div>
  <a href="/nl/nl/p/google-pixel-9a-128gb-zwart/9300000228637472/">
    <h2 class="title">Google Pixel 9a - 128GB - Zwart</h2>
  </a>
  <span aria-label="De prijs van dit productvariant is &#x27;409&#x27; euro en &#x27;00&#x27; cent"></span>
</div>
<div>
  <a href="/nl/nl/p/google-pixel-10-128gb-blauw/9300000238634864/">
    <h2 class="title">Google Pixel 10 - 128GB - Blauw</h2>
  </a>
  <span aria-label="De prijs van dit productvariant is &#x27;628&#x27; euro en &#x27;49&#x27; cent"></span>
</div>
</body></html>
"""

BOL_HTML_NO_RESULTS = "<html><body><p>Geen resultaten</p></body></html>"


def test_parse_products_extracts_price_and_url():
    results = _parse_products(BOL_HTML)
    assert len(results) == 2
    assert results[0].price == 409.00
    assert results[0].currency == "EUR"
    assert results[0].url == "https://www.bol.com/nl/nl/p/google-pixel-9a-128gb-zwart/9300000228637472/"
    assert results[0].source == "bol.com"
    assert results[1].price == 628.49


def test_parse_products_title_from_h2():
    results = _parse_products(BOL_HTML)
    assert "Google Pixel 9a" in results[0].title


def test_parse_products_empty_html():
    assert _parse_products(BOL_HTML_NO_RESULTS) == []


async def test_search_returns_results():
    source = BolSource()
    with aioresponses() as m:
        m.get(
            "https://www.bol.com/nl/nl/s/?searchtext=Google+Pixel",
            body=BOL_HTML,
            content_type="text/html",
        )
        results = await source.search(TEXT_QUERY)
    assert len(results) == 2
    assert all(r.source == "bol.com" for r in results)
    assert all(r.price is not None for r in results)
    assert all(r.currency == "EUR" for r in results)


async def test_search_ean_query():
    source = BolSource()
    with aioresponses() as m:
        m.get(
            "https://www.bol.com/nl/nl/s/?searchtext=8710447308431",
            body=BOL_HTML,
            content_type="text/html",
        )
        results = await source.search(EAN_QUERY)
    assert isinstance(results, list)


async def test_http_error_returns_empty():
    source = BolSource()
    with aioresponses() as m:
        m.get("https://www.bol.com/nl/nl/s/?searchtext=Google+Pixel", status=503)
        results = await source.search(TEXT_QUERY)
    assert results == []
