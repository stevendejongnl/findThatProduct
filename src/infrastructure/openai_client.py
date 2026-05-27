import os
import openai


class TokenBudgetExceeded(Exception):
    pass


class OpenAIQuotaError(Exception):
    pass


def get_openai_client() -> openai.AsyncOpenAI | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return openai.AsyncOpenAI(api_key=key)


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def check_budget(prompt: str, max_tokens: int) -> None:
    estimated = estimate_tokens(prompt)
    if estimated > max_tokens:
        raise TokenBudgetExceeded(
            f"Estimated prompt tokens ({estimated}) exceed budget ({max_tokens})"
        )
