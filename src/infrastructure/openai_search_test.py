import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.infrastructure.openai_search import OpenAISearchSource
from src.domain.search_query import SearchQuery


@pytest.fixture
def query():
    return SearchQuery.from_raw("samsung galaxy buds2 pro")


async def test_returns_empty_list_when_no_api_key(query):
    with patch.dict(os.environ, {}, clear=True):
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        source = OpenAISearchSource()
        results = await source.search(query)
    assert results == []


async def test_returns_parsed_results(query):
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
[
  {"title": "Samsung Galaxy Buds2 Pro", "price": 169.99, "currency": "EUR", "url": "https://bol.com/buds2pro"}
]
"""
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.infrastructure.openai_search.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_SEARCH": "1000", "OPENAI_TOKEN_BUDGET": "2000"}):
            source = OpenAISearchSource()
            results = await source.search(query)

    assert len(results) == 1
    assert results[0].title == "Samsung Galaxy Buds2 Pro"
    assert results[0].price == 169.99
    assert results[0].source == "openai"


async def test_returns_empty_list_on_api_error(query):
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

    with patch("src.infrastructure.openai_search.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_SEARCH": "1000", "OPENAI_TOKEN_BUDGET": "2000"}):
            source = OpenAISearchSource()
            results = await source.search(query)

    assert results == []


async def test_returns_empty_list_when_budget_exceeded(query):
    mock_client = AsyncMock()

    with patch("src.infrastructure.openai_search.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_SEARCH": "1000", "OPENAI_TOKEN_BUDGET": "1"}):
            source = OpenAISearchSource()
            results = await source.search(query)

    assert results == []
    mock_client.chat.completions.create.assert_not_called()


async def test_max_tokens_sent_in_request(query):
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "[]"
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[mock_choice])
    )

    with patch("src.infrastructure.openai_search.get_openai_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MAX_TOKENS_SEARCH": "750", "OPENAI_TOKEN_BUDGET": "2000"}):
            source = OpenAISearchSource()
            await source.search(query)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 750
