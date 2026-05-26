from unittest.mock import AsyncMock
from src.application.search_use_case import SearchUseCase
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery, QueryType


def make_query(raw: str = "8710447308431", type: QueryType = QueryType.EAN) -> SearchQuery:
    return SearchQuery(raw=raw, type=type)


def make_result(url: str, price: float | None) -> ProductResult:
    return ProductResult(title="Product", url=url, source="test", price=price)


async def test_queries_all_sources():
    source_a = AsyncMock()
    source_a.search.return_value = [make_result("https://a.com", 4.99)]
    source_b = AsyncMock()
    source_b.search.return_value = [make_result("https://b.com", 6.00)]

    use_case = SearchUseCase(sources=[source_a, source_b])
    results = await use_case.execute(make_query())

    source_a.search.assert_called_once()
    source_b.search.assert_called_once()
    assert len(results) == 2


async def test_results_sorted_by_price():
    source = AsyncMock()
    source.search.return_value = [
        make_result("https://b.com", 9.99),
        make_result("https://a.com", 2.99),
    ]
    use_case = SearchUseCase(sources=[source])
    results = await use_case.execute(make_query())
    assert results[0].price == 2.99
    assert results[1].price == 9.99


async def test_source_failure_is_isolated():
    failing_source = AsyncMock()
    failing_source.search.side_effect = Exception("Network error")
    good_source = AsyncMock()
    good_source.search.return_value = [make_result("https://good.com", 5.00)]

    use_case = SearchUseCase(sources=[failing_source, good_source])
    results = await use_case.execute(make_query())

    assert len(results) == 1
    assert results[0].url == "https://good.com"


async def test_empty_sources_returns_empty():
    use_case = SearchUseCase(sources=[])
    results = await use_case.execute(make_query())
    assert results == []
