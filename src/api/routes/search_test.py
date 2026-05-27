import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.domain.product import ProductResult
from src.application.enrichment import EnrichmentResult


def make_result(price: float | None = 4.99) -> ProductResult:
    return ProductResult(
        title="Test Product",
        url="https://example.com",
        source="test",
        price=price,
        currency="EUR",
    )


def client():
    app = create_app()
    return TestClient(app)


def test_search_returns_200():
    c = client()
    with patch("src.api.routes.search.SearchUseCase") as MockUseCase:
        instance = AsyncMock()
        instance.execute.return_value = [make_result()]
        MockUseCase.return_value = instance
        resp = c.post("/api/search", json={"query": "8710447308431"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "8710447308431"
    assert body["query_type"] == "ean"
    assert len(body["results"]) == 1
    assert body["results"][0]["title"] == "Test Product"


def test_search_text_query():
    c = client()
    with patch("src.api.routes.search.SearchUseCase") as MockUseCase:
        instance = AsyncMock()
        instance.execute.return_value = [make_result()]
        MockUseCase.return_value = instance
        resp = c.post("/api/search", json={"query": "peanut butter"})
    assert resp.status_code == 200
    assert resp.json()["query_type"] == "text"


def test_search_short_query_returns_422():
    c = client()
    resp = c.post("/api/search", json={"query": "a"})
    assert resp.status_code == 422


def test_search_empty_query_returns_422():
    c = client()
    resp = c.post("/api/search", json={"query": ""})
    assert resp.status_code == 422


def test_search_response_includes_alternatives_field():
    """Verify the response always includes alternatives/enriched/warnings fields."""
    c = client()
    with patch("src.api.routes.search.SearchUseCase") as mock_use_case_cls:
        with patch("src.api.routes.search.EnrichmentService") as mock_enrichment_cls:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = [make_result()]
            mock_use_case_cls.return_value = mock_use_case

            mock_service = AsyncMock()
            mock_service.enrich = AsyncMock(
                return_value=EnrichmentResult(results=[make_result()], alternatives=[], enriched=False)
            )
            mock_enrichment_cls.return_value = mock_service

            resp = c.post("/api/search", json={"query": "test product"})

    assert resp.status_code == 200
    data = resp.json()
    assert "alternatives" in data
    assert "enriched" in data
    assert "warnings" in data


def _parse_sse(text: str) -> list[dict]:
    events = []
    current: dict = {}
    for line in text.splitlines():
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = line[len("data:"):].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


def test_stream_cache_hit_returns_result_immediately():
    from src.api.routes import search as search_module
    from src.application.enrichment import EnrichmentResult
    search_module.CACHE._store["peanut butter"] = (
        __import__("time").monotonic() + 3600,
        EnrichmentResult(results=[make_result()], alternatives=[], enriched=False),
    )
    c = client()
    resp = c.get("/api/search/stream?q=peanut+butter")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    events = _parse_sse(resp.text)
    result_events = [e for e in events if e["event"] == "result"]
    queued_events = [e for e in events if e["event"] == "queued"]
    assert len(result_events) == 1
    assert len(queued_events) == 0
    data = json.loads(result_events[0]["data"])
    assert data["query"] == "peanut butter"
    assert len(data["results"]) == 1


def test_stream_missing_query_returns_422():
    c = client()
    resp = c.get("/api/search/stream")
    assert resp.status_code == 422


def test_stream_short_query_returns_422():
    c = client()
    resp = c.get("/api/search/stream?q=a")
    assert resp.status_code == 422
