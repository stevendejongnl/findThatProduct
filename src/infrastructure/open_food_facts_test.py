from aioresponses import aioresponses
from src.infrastructure.open_food_facts import OpenFoodFactsSource
from src.domain.search_query import SearchQuery, QueryType


def ean_query() -> SearchQuery:
    return SearchQuery(raw="8710447308431", type=QueryType.EAN)


def text_query() -> SearchQuery:
    return SearchQuery(raw="peanut butter", type=QueryType.TEXT)


async def test_ean_query_returns_results():
    source = OpenFoodFactsSource()
    with aioresponses() as m:
        m.get(
            "https://world.openfoodfacts.org/api/v2/product/8710447308431.json",
            payload={
                "status": 1,
                "product": {
                    "product_name": "Peanut Butter",
                    "image_url": "https://example.com/img.jpg",
                    "url": "https://world.openfoodfacts.org/product/8710447308431",
                },
            },
        )
        results = await source.search(ean_query())
    assert len(results) == 1
    assert results[0].title == "Peanut Butter"
    assert results[0].source == "open_food_facts"
    assert results[0].ean == "8710447308431"
    assert results[0].price is None


async def test_product_not_found_returns_empty():
    source = OpenFoodFactsSource()
    with aioresponses() as m:
        m.get(
            "https://world.openfoodfacts.org/api/v2/product/0000000000000.json",
            payload={"status": 0},
        )
        results = await source.search(SearchQuery(raw="0000000000000", type=QueryType.EAN))
    assert results == []


async def test_text_query_returns_empty():
    source = OpenFoodFactsSource()
    results = await source.search(text_query())
    assert results == []


async def test_http_error_returns_empty():
    source = OpenFoodFactsSource()
    with aioresponses() as m:
        m.get(
            "https://world.openfoodfacts.org/api/v2/product/8710447308431.json",
            status=500,
        )
        results = await source.search(ean_query())
    assert results == []
