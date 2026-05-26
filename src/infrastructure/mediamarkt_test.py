import json
from aioresponses import aioresponses
from src.infrastructure.mediamarkt import MediaMarktSource, _parse_products
from src.domain.search_query import SearchQuery, QueryType

TEXT_QUERY = SearchQuery(raw="Google Pixel", type=QueryType.TEXT)

ITEM_LIST = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "itemListElement": [
        {
            "@type": "ListItem",
            "position": 1,
            "item": {
                "@type": "Product",
                "name": "GOOGLE Pixel 10 - 5G - 256 GB Zwart",
                "url": "https://www.mediamarkt.nl/nl/product/_google-pixel-10-5g-256-gb-zwart-1888659.html",
                "image": "https://assets.mmsrg.com/img/pixel10.jpg",
                "offers": {"@type": "Offer", "price": 659, "priceCurrency": "EUR"},
            },
        },
        {
            "@type": "ListItem",
            "position": 2,
            "item": {
                "@type": "Product",
                "name": "GOOGLE Pixel 9a - 5G - 128 GB Zwart",
                "url": "https://www.mediamarkt.nl/nl/product/_google-pixel-9a-zwart-1876543.html",
                "image": None,
                "offers": {"@type": "Offer", "price": 499, "priceCurrency": "EUR"},
            },
        },
    ],
}

MM_HTML = f'<html><body><script type="application/ld+json">{json.dumps(ITEM_LIST)}</script></body></html>'
MM_HTML_EMPTY = "<html><body><p>Geen resultaten</p></body></html>"


def test_parse_products_extracts_name_price_url():
    results = _parse_products(MM_HTML)
    assert len(results) == 2
    assert results[0].title == "GOOGLE Pixel 10 - 5G - 256 GB Zwart"
    assert results[0].price == 659.0
    assert results[0].currency == "EUR"
    assert "mediamarkt.nl" in results[0].url
    assert results[0].source == "mediamarkt.nl"


def test_parse_products_no_jsonld():
    assert _parse_products(MM_HTML_EMPTY) == []


def test_parse_products_image_optional():
    results = _parse_products(MM_HTML)
    assert results[0].image_url is not None
    assert results[1].image_url is None


async def test_search_returns_results():
    source = MediaMarktSource()
    with aioresponses() as m:
        m.get(
            "https://www.mediamarkt.nl/nl/search.html?query=Google+Pixel",
            body=MM_HTML,
            content_type="text/html",
        )
        results = await source.search(TEXT_QUERY)
    assert len(results) == 2
    assert all(r.source == "mediamarkt.nl" for r in results)
    assert all(r.price is not None for r in results)


async def test_http_error_returns_empty():
    source = MediaMarktSource()
    with aioresponses() as m:
        m.get("https://www.mediamarkt.nl/nl/search.html?query=Google+Pixel", status=503)
        results = await source.search(TEXT_QUERY)
    assert results == []
