from src.application.aggregator import AggregatorService
from src.domain.product import ProductResult


def make_result(url: str, price: float | None, source: str = "test") -> ProductResult:
    return ProductResult(title="Product", url=url, source=source, price=price)


def test_sorted_by_price_ascending():
    results = [
        make_result("https://a.com", 9.99),
        make_result("https://b.com", 4.99),
        make_result("https://c.com", 6.50),
    ]
    aggregated = AggregatorService.aggregate(results)
    prices = [r.price for r in aggregated]
    assert prices == [4.99, 6.50, 9.99]


def test_none_price_sorted_last():
    results = [
        make_result("https://a.com", None),
        make_result("https://b.com", 4.99),
    ]
    aggregated = AggregatorService.aggregate(results)
    assert aggregated[0].price == 4.99
    assert aggregated[1].price is None


def test_deduplicates_by_url():
    results = [
        make_result("https://a.com", 4.99, "source1"),
        make_result("https://a.com", 3.99, "source2"),
        make_result("https://b.com", 6.00),
    ]
    aggregated = AggregatorService.aggregate(results)
    urls = [r.url for r in aggregated]
    assert len(urls) == 2
    assert urls.count("https://a.com") == 1


def test_empty_input_returns_empty():
    assert AggregatorService.aggregate([]) == []


def test_all_none_prices_returned():
    results = [
        make_result("https://a.com", None),
        make_result("https://b.com", None),
    ]
    aggregated = AggregatorService.aggregate(results)
    assert len(aggregated) == 2
