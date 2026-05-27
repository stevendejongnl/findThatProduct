from src.api.schemas import SearchResponse, AlternativeSchema, ExplainRequest, ExplainResponse


def test_search_response_defaults():
    resp = SearchResponse(query="test", query_type="text", results=[])
    assert resp.alternatives == []
    assert resp.enriched is False
    assert resp.warnings == []


def test_alternative_schema():
    alt = AlternativeSchema(
        title="Sony WF-1000XM5",
        reason="Cheaper",
        price=149.0,
        currency="EUR",
        url="https://example.com",
        source="openai",
    )
    assert alt.source == "openai"


def test_explain_response_defaults():
    resp = ExplainResponse(explanation="Good deal")
    assert resp.warnings == []


def test_explain_response_null_explanation():
    resp = ExplainResponse(explanation=None, warnings=["quota exceeded"])
    assert resp.explanation is None
