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
