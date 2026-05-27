import logging
import os
import openai
from fastapi import APIRouter
from src.api.schemas import ExplainRequest, ExplainResponse
from src.infrastructure.openai_client import get_openai_client, check_budget, TokenBudgetExceeded

logger = logging.getLogger(__name__)
router = APIRouter()

_SYSTEM_PROMPT = (
    "You are a shopping assistant. Given a product title, URL, price, and the user's original query, "
    "briefly explain whether this is a good deal. Mention the price context, any alternatives worth considering, "
    "and a clear recommendation. Keep it under 3 sentences."
)


@router.post("/explain", response_model=ExplainResponse)
async def explain(request: ExplainRequest) -> ExplainResponse:
    client = get_openai_client()
    if client is None:
        return ExplainResponse(explanation=None)

    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS_EXPLAIN", "300"))
    budget = int(os.getenv("OPENAI_TOKEN_BUDGET", "2000"))
    price_str = f"€{request.price}" if request.price is not None else "unknown price"
    prompt = (
        f"Query: {request.query}\n"
        f"Product: {request.title}\n"
        f"Price: {price_str}\n"
        f"URL: {request.url}"
    )

    try:
        check_budget(prompt=_SYSTEM_PROMPT + prompt, max_tokens=budget)
    except TokenBudgetExceeded as e:
        logger.warning("OpenAI explain skipped: %s", e)
        return ExplainResponse(
            explanation=None,
            warnings=["OpenAI explain skipped: estimated prompt exceeds token budget"],
        )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        explanation = response.choices[0].message.content or None
        return ExplainResponse(explanation=explanation)
    except openai.RateLimitError as e:
        logger.warning("OpenAI explain quota/rate limit: %s", e)
        return ExplainResponse(
            explanation=None,
            warnings=["OpenAI explain skipped: rate limit or quota exceeded"],
        )
    except Exception as e:
        logger.warning("OpenAI explain failed: %s", e)
        return ExplainResponse(
            explanation=None,
            warnings=[f"OpenAI explain failed: {e}"],
        )
