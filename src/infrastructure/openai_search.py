import json
import logging
import os
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery
from src.domain.search_source import SearchSource
from src.infrastructure.openai_client import get_openai_client, check_budget, TokenBudgetExceeded

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a product search assistant. Given a product query, find real products "
    "available for purchase online. Return ONLY a JSON array, no explanation, no markdown. "
    "Each object must have: title (str), price (float or null), currency (str, default EUR), url (str). "
    "Return at most 5 results. If you cannot find results, return an empty array []."
)


class OpenAISearchSource(SearchSource):
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        client = get_openai_client()
        if client is None:
            return []

        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS_SEARCH", "1000"))
        budget = int(os.getenv("OPENAI_TOKEN_BUDGET", "2000"))
        prompt = f"Find products matching: {query.raw}"

        try:
            check_budget(prompt=_SYSTEM_PROMPT + prompt, max_tokens=budget)
        except TokenBudgetExceeded as e:
            logger.warning("OpenAI search skipped: %s", e)
            return []

        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content or "[]"
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            items = json.loads(raw)
            results = []
            for item in items:
                if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
                    continue
                results.append(ProductResult(
                    title=item["title"],
                    url=item["url"],
                    source="openai",
                    price=item.get("price"),
                    currency=item.get("currency", "EUR"),
                ))
            return results
        except Exception as e:
            logger.warning("OpenAISearchSource failed: %s", e)
            return []
