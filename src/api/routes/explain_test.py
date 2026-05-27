import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from src.api.main import app


async def test_explain_returns_explanation():
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "At €169.99 this is a fair price for Samsung's flagship earbuds."
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.api.routes.explain.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_EXPLAIN": "300", "OPENAI_TOKEN_BUDGET": "2000"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/explain", json={
                    "title": "Samsung Galaxy Buds2 Pro",
                    "url": "https://bol.com/a",
                    "price": 169.99,
                    "query": "samsung buds2 pro",
                })

    assert resp.status_code == 200
    data = resp.json()
    assert "At €169.99" in data["explanation"]
    assert data["warnings"] == []


async def test_explain_returns_null_explanation_on_quota_error():
    import openai
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError("quota", response=MagicMock(), body={})
    )

    with patch("src.api.routes.explain.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_EXPLAIN": "300", "OPENAI_TOKEN_BUDGET": "2000"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/explain", json={
                    "title": "Samsung Galaxy Buds2 Pro",
                    "url": "https://bol.com/a",
                    "price": 169.99,
                    "query": "samsung buds2 pro",
                })

    assert resp.status_code == 200
    data = resp.json()
    assert data["explanation"] is None
    assert len(data["warnings"]) > 0


async def test_explain_returns_null_when_budget_exceeded():
    mock_client = AsyncMock()

    with patch("src.api.routes.explain.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_EXPLAIN": "300", "OPENAI_TOKEN_BUDGET": "1"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/explain", json={
                    "title": "Samsung Galaxy Buds2 Pro",
                    "url": "https://bol.com/a",
                    "price": 169.99,
                    "query": "samsung buds2 pro",
                })

    assert resp.status_code == 200
    data = resp.json()
    assert data["explanation"] is None
    assert any("budget" in w.lower() for w in data["warnings"])


async def test_explain_returns_null_when_no_api_key():
    with patch.dict(os.environ, {}, clear=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/explain", json={
                "title": "Some Product",
                "url": "https://example.com",
                "price": 99.0,
                "query": "some product",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["explanation"] is None
