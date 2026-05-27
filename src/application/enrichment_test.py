import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.application.enrichment import EnrichmentService, EnrichmentResult
from src.domain.product import ProductResult


@pytest.fixture
def results():
    return [
        ProductResult(title="Samsung Galaxy Buds2 Pro", url="https://bol.com/a", source="bol", price=169.99),
        ProductResult(title="Galaxy Buds 2 Pro", url="https://coolblue.nl/b", source="coolblue", price=175.0),
    ]


async def test_returns_original_results_when_no_api_key(results):
    with patch.dict(os.environ, {}, clear=True):
        service = EnrichmentService()
        result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is False
    assert result.alternatives == []
    assert result.warnings == []
    assert len(result.results) == 2


async def test_returns_cleaned_results_and_alternatives(results):
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
{
  "results": [
    {"title": "Samsung Galaxy Buds2 Pro", "price": 169.99, "currency": "EUR", "url": "https://bol.com/a", "source": "bol", "image_url": null, "ean": null}
  ],
  "alternatives": [
    {"title": "Sony WF-1000XM5", "reason": "Similar ANC at lower price", "price": 149.0, "currency": "EUR", "url": "https://bol.com/sony"}
  ]
}
"""
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "2000"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is True
    assert len(result.results) == 1
    assert len(result.alternatives) == 1
    assert result.alternatives[0].title == "Sony WF-1000XM5"
    assert result.warnings == []


async def test_returns_original_results_on_api_error(results):
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "2000"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is False
    assert result.alternatives == []
    assert len(result.results) == 2
    assert "enrichment failed" in result.warnings[0].lower()


async def test_returns_warning_when_budget_exceeded(results):
    mock_client = AsyncMock()

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "1"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is False
    assert "budget" in result.warnings[0].lower()
    mock_client.chat.completions.create.assert_not_called()


async def test_preserves_original_source_in_cleaned_results(results):
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
{
  "results": [
    {"title": "Samsung Galaxy Buds2 Pro", "price": 169.99, "currency": "EUR", "url": "https://bol.com/a", "source": "openai"}
  ],
  "alternatives": []
}
"""
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "2000"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    # Source "bol" from original result should be preserved over model's "openai" output
    assert result.results[0].source == "bol"


async def test_strips_markdown_fences_from_response(results):
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"results": [{"title": "Samsung Galaxy Buds2 Pro", "price": 169.99, "currency": "EUR", "url": "https://bol.com/a", "source": "bol", "image_url": null, "ean": null}], "alternatives": []}\n```'
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "2000"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is True
    assert len(result.results) == 1
    assert result.warnings == []


async def test_returns_original_results_on_invalid_json(results):
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "```json\n{broken json"
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "2000"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is False
    assert len(result.results) == 2
    assert "invalid json" in result.warnings[0].lower()


async def test_returns_warning_on_quota_error(results):
    import openai
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError("quota exceeded", response=MagicMock(), body={})
    )

    with patch("src.application.enrichment.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_ENRICH": "1500", "OPENAI_TOKEN_BUDGET": "2000"}):
            service = EnrichmentService()
            result = await service.enrich("samsung buds2 pro", results)

    assert result.enriched is False
    assert any("quota" in w.lower() or "rate limit" in w.lower() for w in result.warnings)
