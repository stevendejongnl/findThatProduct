import os
import openai

_client: openai.AsyncOpenAI | None = None


class TokenBudgetExceeded(Exception):
    pass


class OpenAIQuotaError(Exception):
    """Raised by callers when OpenAI returns a rate-limit or quota error."""
    pass


def get_openai_client() -> openai.AsyncOpenAI | None:
    global _client
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=key)
    return _client


def estimate_tokens(text: str) -> int:
    # Approximation: 4 ASCII chars ≈ 1 token. Good enough for budget checks.
    return len(text) // 4


def check_budget(prompt: str, max_tokens: int) -> None:
    estimated = estimate_tokens(prompt)
    if estimated > max_tokens:
        raise TokenBudgetExceeded(
            f"Estimated prompt tokens ({estimated}) exceed budget ({max_tokens})"
        )
