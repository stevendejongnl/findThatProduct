import json
import logging
import os
from dataclasses import dataclass, field
import openai
from src.domain.product import ProductResult
from src.domain.alternative_result import AlternativeResult
from src.infrastructure.openai_client import get_openai_client, check_budget, TokenBudgetExceeded

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a product search assistant. You receive a list of product results and a search query. "
    "Your tasks: (1) Clean and normalize the results list — fix inconsistent titles, remove true duplicates. "
    "(2) Suggest up to 3 alternative products the user might not have found. "
    "Return valid JSON only (no markdown) with this structure:\n"
    '{"results": [{title, price, currency, url, source, image_url, ean}], '
    '"alternatives": [{title, reason, price, currency, url}]}'
)


@dataclass
class EnrichmentResult:
    results: list[ProductResult]
    alternatives: list[AlternativeResult] = field(default_factory=list)
    enriched: bool = False
    warnings: list[str] = field(default_factory=list)


class EnrichmentService:
    async def enrich(self, query: str | None, results: list[ProductResult]) -> EnrichmentResult:
        if query is None:
            return EnrichmentResult(results=results)

        client = get_openai_client()
        if client is None:
            return EnrichmentResult(results=results)

        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS_ENRICH", "1500"))
        budget = int(os.getenv("OPENAI_TOKEN_BUDGET", "2000"))

        results_summary = json.dumps([
            {"title": r.title, "price": r.price, "currency": r.currency, "url": r.url, "source": r.source}
            for r in results
        ])
        prompt = f"Query: {query}\nResults:\n{results_summary}"

        try:
            check_budget(prompt=_SYSTEM_PROMPT + prompt, max_tokens=budget)
        except TokenBudgetExceeded as e:
            logger.warning("OpenAI enrichment skipped: %s", e)
            return EnrichmentResult(
                results=results,
                warnings=[f"OpenAI enrichment skipped: estimated prompt exceeds token budget"],
            )

        url_to_source = {r.url: r.source for r in results}

        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content or "{}"
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.warning("EnrichmentService: invalid JSON from OpenAI: %s", e)
                return EnrichmentResult(
                    results=results,
                    warnings=["OpenAI enrichment failed: invalid JSON response"],
                )

            cleaned = []
            for item in data.get("results", []):
                if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
                    continue
                url = item["url"]
                cleaned.append(ProductResult(
                    title=item["title"],
                    url=url,
                    source=url_to_source.get(url, item.get("source", "openai")),
                    price=item.get("price"),
                    currency=item.get("currency", "EUR"),
                    image_url=item.get("image_url"),
                    ean=item.get("ean"),
                ))

            alternatives = []
            for item in data.get("alternatives", []):
                if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
                    continue
                alternatives.append(AlternativeResult(
                    title=item["title"],
                    reason=item.get("reason", ""),
                    url=item["url"],
                    price=item.get("price"),
                    currency=item.get("currency", "EUR"),
                ))

            return EnrichmentResult(
                results=cleaned if cleaned else results,
                alternatives=alternatives,
                enriched=True,
            )

        except openai.RateLimitError as e:
            logger.warning("OpenAI quota/rate limit: %s", e)
            return EnrichmentResult(
                results=results,
                warnings=["OpenAI enrichment skipped: rate limit or quota exceeded"],
            )
        except Exception as e:
            logger.warning("EnrichmentService failed: %s", e)
            return EnrichmentResult(
                results=results,
                warnings=[f"OpenAI enrichment failed: {e}"],
            )
