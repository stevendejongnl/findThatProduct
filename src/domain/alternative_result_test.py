from src.domain.alternative_result import AlternativeResult


def test_alternative_result_defaults():
    alt = AlternativeResult(
        title="Sony WF-1000XM5",
        reason="Similar ANC earbuds at lower price",
        url="https://example.com",
    )
    assert alt.source == "openai"
    assert alt.currency == "EUR"
    assert alt.price is None


def test_alternative_result_with_price():
    alt = AlternativeResult(
        title="Sony WF-1000XM5",
        reason="Cheaper alternative",
        url="https://example.com",
        price=189.0,
    )
    assert alt.price == 189.0


def test_alternative_result_with_all_fields():
    alt = AlternativeResult(
        title="Sony WF-1000XM5",
        reason="Better value",
        url="https://example.com/sony",
        price=149.0,
        currency="USD",
        source="manual",
    )
    assert alt.title == "Sony WF-1000XM5"
    assert alt.reason == "Better value"
    assert alt.url == "https://example.com/sony"
    assert alt.price == 149.0
    assert alt.currency == "USD"
    assert alt.source == "manual"
