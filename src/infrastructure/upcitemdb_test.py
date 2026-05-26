from aioresponses import aioresponses
from src.infrastructure.upcitemdb import UPCitemdbSource
from src.domain.search_query import SearchQuery, QueryType


def ean_query() -> SearchQuery:
    return SearchQuery(raw="4006381333931", type=QueryType.EAN)


async def test_ean_returns_results():
    source = UPCitemdbSource()
    with aioresponses() as m:
        m.get(
            "https://api.upcitemdb.com/prod/trial/lookup?upc=4006381333931",
            payload={
                "code": "OK",
                "items": [
                    {
                        "title": "Stabilo Boss",
                        "offers": [{"price": "2.99", "merchant": "amazon"}],
                        "images": ["https://example.com/img.jpg"],
                    }
                ],
            },
        )
        results = await source.search(ean_query())
    assert len(results) == 1
    assert results[0].title == "Stabilo Boss"
    assert results[0].price == 2.99
    assert results[0].source == "upcitemdb"


async def test_no_items_returns_empty():
    source = UPCitemdbSource()
    with aioresponses() as m:
        m.get(
            "https://api.upcitemdb.com/prod/trial/lookup?upc=0000000000000",
            payload={"code": "OK", "items": []},
        )
        results = await source.search(SearchQuery(raw="0000000000000", type=QueryType.EAN))
    assert results == []


async def test_http_error_returns_empty():
    source = UPCitemdbSource()
    with aioresponses() as m:
        m.get(
            "https://api.upcitemdb.com/prod/trial/lookup?upc=4006381333931",
            status=429,
        )
        results = await source.search(ean_query())
    assert results == []


async def test_text_query_returns_empty():
    source = UPCitemdbSource()
    results = await source.search(SearchQuery(raw="peanut butter", type=QueryType.TEXT))
    assert results == []
