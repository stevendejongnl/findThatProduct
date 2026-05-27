import os
import pytest
from unittest.mock import patch
import src.infrastructure.openai_client as openai_client_module
from src.infrastructure.openai_client import (
    get_openai_client,
    estimate_tokens,
    TokenBudgetExceeded,
    check_budget,
)


@pytest.fixture(autouse=True)
def reset_client_singleton():
    openai_client_module._client = None
    yield
    openai_client_module._client = None


def test_get_openai_client_returns_none_without_key():
    with patch.dict(os.environ, {}, clear=True):
        client = get_openai_client()
    assert client is None


def test_get_openai_client_returns_client_with_key():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        client = get_openai_client()
    assert client is not None


def test_estimate_tokens_approximation():
    # 4 chars per token approximation
    text = "a" * 400
    assert estimate_tokens(text) == 100


def test_check_budget_raises_when_exceeded():
    with pytest.raises(TokenBudgetExceeded):
        check_budget(prompt="x" * 4000, max_tokens=500)  # 1000 estimated > 500


def test_check_budget_passes_when_within_budget():
    check_budget(prompt="x" * 400, max_tokens=500)  # 100 estimated < 500
