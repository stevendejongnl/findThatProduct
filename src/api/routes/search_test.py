from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.domain.product import ProductResult


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
