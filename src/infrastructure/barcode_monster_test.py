from aioresponses import aioresponses
from src.infrastructure.barcode_monster import BarcodeMonsterSource
from src.domain.search_query import SearchQuery, QueryType


def ean_query() -> SearchQuery:
    return SearchQuery(raw="8710447308431", type=QueryType.EAN)


async def test_ean_returns_result():
    source = BarcodeMonsterSource()
    with aioresponses() as m:
        m.get(
            "https://barcode.monster/api/8710447308431",
            payload={"description": "Calve Pindakaas", "type": "EAN-13"},
        )
        results = await source.search(ean_query())
    assert len(results) == 1
    assert results[0].title == "Calve Pindakaas"
    assert results[0].source == "barcode_monster"
    assert results[0].price is None


async def test_missing_description_returns_empty():
    source = BarcodeMonsterSource()
    with aioresponses() as m:
        m.get(
            "https://barcode.monster/api/8710447308431",
            payload={"type": "EAN-13"},
        )
        results = await source.search(ean_query())
    assert results == []


async def test_http_error_returns_empty():
    source = BarcodeMonsterSource()
    with aioresponses() as m:
        m.get("https://barcode.monster/api/8710447308431", status=404)
        results = await source.search(ean_query())
    assert results == []


async def test_text_query_returns_empty():
    source = BarcodeMonsterSource()
    results = await source.search(SearchQuery(raw="peanut butter", type=QueryType.TEXT))
    assert results == []
