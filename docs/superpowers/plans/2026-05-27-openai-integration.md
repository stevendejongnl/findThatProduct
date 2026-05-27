# OpenAI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenAI as a parallel search source, a post-aggregation enrichment layer (clean results + suggest alternatives), a lazy per-result explain endpoint, and token budget enforcement with warnings surfaced in the API response.

**Architecture:** `OpenAISearchSource` implements the existing `SearchSource` ABC and runs in parallel with all other sources. After aggregation, `EnrichmentService` calls GPT-4o once to clean results and generate alternatives. A new `/api/explain` endpoint handles lazy per-result deal analysis. All OpenAI calls share a single client factory that enforces a token budget pre-flight and surfaces quota errors as named warnings in the response.

**Tech Stack:** Python 3.12, FastAPI, `openai` SDK (async), `tiktoken` for token estimation, Pydantic v2, pytest + aioresponses for mocking.

---

## File Map

**New files:**
- `src/domain/alternative_result.py` — `AlternativeResult` dataclass
- `src/infrastructure/openai_client.py` — shared async OpenAI client factory, token estimator, custom exceptions
- `src/infrastructure/openai_search.py` — `OpenAISearchSource` (implements `SearchSource`)
- `src/infrastructure/openai_search_test.py` — tests for `OpenAISearchSource`
- `src/application/enrichment.py` — `EnrichmentService`
- `src/application/enrichment_test.py` — tests for `EnrichmentService`
- `src/api/routes/explain.py` — `POST /api/explain`
- `src/api/routes/explain_test.py` — tests for explain route
- `frontend/src/ui/AlternativeCard.ts` — renders one alternative
- `frontend/src/ui/AlternativeCard.test.ts`
- `frontend/src/ui/AlternativesList.ts` — renders alternatives section
- `frontend/src/ui/AlternativesList.test.ts`
- `frontend/src/ui/ExplainPopup.ts` — modal with loading/content/error states
- `frontend/src/ui/ExplainPopup.test.ts`

**Modified files:**
- `src/api/schemas.py` — add `AlternativeSchema`, `ExplainRequest`, `ExplainResponse`; extend `SearchResponse` with `alternatives`, `enriched`, `warnings`
- `src/api/routes/search.py` — wire `OpenAISearchSource` + `EnrichmentService`, return extended response
- `src/api/main.py` — register `/api/explain` router
- `frontend/src/ui/ResultCard.ts` — add "Why is this a good deal?" button
- `frontend/src/ui/ResultsList.ts` — render alternatives section + warnings banner
- `frontend/src/application/search.ts` — handle new `alternatives`/`enriched`/`warnings` fields
- `pyproject.toml` — add `openai` and `tiktoken` dependencies

---

## Task 1: Add `openai` and `tiktoken` dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependencies**

```bash
uv add openai tiktoken
```

- [ ] **Step 2: Verify install**

```bash
uv run python -c "import openai, tiktoken; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add openai and tiktoken dependencies"
```

---

## Task 2: `AlternativeResult` domain value object

**Files:**
- Create: `src/domain/alternative_result.py`

- [ ] **Step 1: Write the failing test**

Create `src/domain/alternative_result_test.py`:

```python
from src.domain.alternative_result import AlternativeResult


def test_alternative_result_defaults():
    alt = AlternativeResult(
        title="Sony WF-1000XM5",
        reason="Similar ANC earbuds at lower price",
        url="https://example.com",
    )
    assert alt.source == "openai"
    assert alt.currency == "EUR"
    assert alt.price is None


def test_alternative_result_with_price():
    alt = AlternativeResult(
        title="Sony WF-1000XM5",
        reason="Cheaper alternative",
        url="https://example.com",
        price=189.0,
    )
    assert alt.price == 189.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest src/domain/alternative_result_test.py -v
```
Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement**

Create `src/domain/alternative_result.py`:

```python
from dataclasses import dataclass, field


@dataclass
class AlternativeResult:
    title: str
    reason: str
    url: str
    price: float | None = None
    currency: str = "EUR"
    source: str = "openai"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest src/domain/alternative_result_test.py -v
```
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/domain/alternative_result.py src/domain/alternative_result_test.py
git commit -m "feat(domain): add AlternativeResult value object"
```

---

## Task 3: OpenAI client factory with token budget enforcement

**Files:**
- Create: `src/infrastructure/openai_client.py`
- Create: `src/infrastructure/openai_client_test.py`

- [ ] **Step 1: Write the failing tests**

Create `src/infrastructure/openai_client_test.py`:

```python
import os
import pytest
from unittest.mock import patch, AsyncMock
from src.infrastructure.openai_client import (
    get_openai_client,
    estimate_tokens,
    TokenBudgetExceeded,
    OpenAIQuotaError,
    check_budget,
)


def test_get_openai_client_returns_none_without_key():
    with patch.dict(os.environ, {}, clear=True):
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest src/infrastructure/openai_client_test.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement**

Create `src/infrastructure/openai_client.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest src/infrastructure/openai_client_test.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/openai_client.py src/infrastructure/openai_client_test.py
git commit -m "feat(infra): add OpenAI client factory with token budget enforcement"
```

---

## Task 4: `OpenAISearchSource`

**Files:**
- Create: `src/infrastructure/openai_search.py`
- Create: `src/infrastructure/openai_search_test.py`

- [ ] **Step 1: Write the failing tests**

Create `src/infrastructure/openai_search_test.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest src/infrastructure/openai_search_test.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement**

Create `src/infrastructure/openai_search.py`:

```python
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
    "available for purchase online. Return a JSON array of objects with keys: "
    "title (str), price (float or null), currency (str, default EUR), url (str). "
    "Return at most 5 results. Return only valid JSON, no markdown."
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
                model="gpt-4o-search-preview",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content or "[]"
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest src/infrastructure/openai_search_test.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/openai_search.py src/infrastructure/openai_search_test.py
git commit -m "feat(infra): add OpenAISearchSource with token budget enforcement"
```

---

## Task 5: `EnrichmentService`

**Files:**
- Create: `src/application/enrichment.py`
- Create: `src/application/enrichment_test.py`

- [ ] **Step 1: Write the failing tests**

Create `src/application/enrichment_test.py`:

```python
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
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest src/application/enrichment_test.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement**

Create `src/application/enrichment.py`:

```python
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
    async def enrich(self, query: str, results: list[ProductResult]) -> EnrichmentResult:
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
            data = json.loads(raw)

            cleaned = []
            for item in data.get("results", []):
                if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
                    continue
                cleaned.append(ProductResult(
                    title=item["title"],
                    url=item["url"],
                    source=item.get("source", "openai"),
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest src/application/enrichment_test.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/application/enrichment.py src/application/enrichment_test.py
git commit -m "feat(application): add EnrichmentService with alternatives and warnings"
```

---

## Task 6: Extend Pydantic schemas

**Files:**
- Modify: `src/api/schemas.py`

Current content of `src/api/schemas.py`:

```python
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str


class ProductResultSchema(BaseModel):
    title: str
    price: float | None
    currency: str
    url: str
    source: str
    image_url: str | None
    ean: str | None


class SearchResponse(BaseModel):
    query: str
    query_type: str
    results: list[ProductResultSchema]
```

- [ ] **Step 1: Write the failing test**

Add to `src/api/schemas_test.py` (create if not exists):

```python
from src.api.schemas import SearchResponse, AlternativeSchema, ExplainRequest, ExplainResponse


def test_search_response_defaults():
    resp = SearchResponse(query="test", query_type="text", results=[])
    assert resp.alternatives == []
    assert resp.enriched is False
    assert resp.warnings == []


def test_alternative_schema():
    alt = AlternativeSchema(
        title="Sony WF-1000XM5",
        reason="Cheaper",
        price=149.0,
        currency="EUR",
        url="https://example.com",
        source="openai",
    )
    assert alt.source == "openai"


def test_explain_response_defaults():
    resp = ExplainResponse(explanation="Good deal")
    assert resp.warnings == []


def test_explain_response_null_explanation():
    resp = ExplainResponse(explanation=None, warnings=["quota exceeded"])
    assert resp.explanation is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest src/api/schemas_test.py -v
```
Expected: `ImportError` on `AlternativeSchema`

- [ ] **Step 3: Implement**

Replace `src/api/schemas.py` with:

```python
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str


class ProductResultSchema(BaseModel):
    title: str
    price: float | None
    currency: str
    url: str
    source: str
    image_url: str | None
    ean: str | None


class AlternativeSchema(BaseModel):
    title: str
    reason: str
    price: float | None
    currency: str
    url: str
    source: str


class SearchResponse(BaseModel):
    query: str
    query_type: str
    results: list[ProductResultSchema]
    alternatives: list[AlternativeSchema] = []
    enriched: bool = False
    warnings: list[str] = []


class ExplainRequest(BaseModel):
    title: str
    url: str
    price: float | None
    query: str


class ExplainResponse(BaseModel):
    explanation: str | None
    warnings: list[str] = []
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest src/api/schemas_test.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/api/schemas.py src/api/schemas_test.py
git commit -m "feat(api): extend schemas with alternatives, enriched, warnings, explain"
```

---

## Task 7: Wire `OpenAISearchSource` + `EnrichmentService` into search route

**Files:**
- Modify: `src/api/routes/search.py`

- [ ] **Step 1: Write the failing test**

Add to `src/api/routes/search_test.py` (create if not exists — uses httpx TestClient):

```python
import os
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from src.api.main import app


async def test_search_response_includes_alternatives_field():
    """Verify the response always includes alternatives/enriched/warnings fields."""
    with patch("src.api.routes.search.EnrichmentService") as mock_enrichment_cls:
        mock_service = AsyncMock()
        from src.application.enrichment import EnrichmentResult
        mock_service.enrich = AsyncMock(return_value=EnrichmentResult(results=[], alternatives=[], enriched=False))
        mock_enrichment_cls.return_value = mock_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/search", json={"query": "test product"})

    assert resp.status_code == 200
    data = resp.json()
    assert "alternatives" in data
    assert "enriched" in data
    assert "warnings" in data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest src/api/routes/search_test.py::test_search_response_includes_alternatives_field -v
```
Expected: FAIL — response missing `alternatives` field

- [ ] **Step 3: Implement**

Replace `src/api/routes/search.py` with:

```python
import os
from fastapi import APIRouter, HTTPException
from src.api.schemas import SearchRequest, SearchResponse, ProductResultSchema, AlternativeSchema
from src.application.search_use_case import SearchUseCase
from src.application.enrichment import EnrichmentService
from src.domain.search_query import SearchQuery, QueryType
from src.domain.search_source import SearchSource
from src.infrastructure.open_food_facts import OpenFoodFactsSource
from src.infrastructure.upcitemdb import UPCitemdbSource
from src.infrastructure.barcode_monster import BarcodeMonsterSource
from src.infrastructure.duckduckgo import DuckDuckGoSource
from src.infrastructure.bol import BolSource
from src.infrastructure.mediamarkt import MediaMarktSource
from src.infrastructure.coolblue import CoolblueSource
from src.infrastructure.alternate import AlternateSource
from src.infrastructure.tweakers import TweakersSource
from src.infrastructure.amazon_nl import AmazonNLSource
from src.infrastructure.openai_search import OpenAISearchSource

router = APIRouter()


def _build_sources() -> list[SearchSource]:
    sources: list[SearchSource] = [
        BolSource(),
        CoolblueSource(),
        MediaMarktSource(),
        AlternateSource(),
        AmazonNLSource(),
        TweakersSource(),
        OpenFoodFactsSource(),
        UPCitemdbSource(),
        BarcodeMonsterSource(),
        DuckDuckGoSource(),
    ]
    if os.getenv("OPENAI_API_KEY"):
        sources.append(OpenAISearchSource())
    return sources


SOURCES = _build_sources()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        query = SearchQuery.from_raw(request.query)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    use_case = SearchUseCase(sources=SOURCES)
    raw_results = await use_case.execute(query)

    enrich_query = "" if query.type == QueryType.EAN else query.raw
    enrichment = EnrichmentService()
    enriched = await enrichment.enrich(enrich_query, raw_results)

    return SearchResponse(
        query=query.raw,
        query_type=query.type.value,
        results=[
            ProductResultSchema(
                title=r.title,
                price=r.price,
                currency=r.currency,
                url=r.url,
                source=r.source,
                image_url=r.image_url,
                ean=r.ean,
            )
            for r in enriched.results
        ],
        alternatives=[
            AlternativeSchema(
                title=a.title,
                reason=a.reason,
                price=a.price,
                currency=a.currency,
                url=a.url,
                source=a.source,
            )
            for a in enriched.alternatives
        ],
        enriched=enriched.enriched,
        warnings=enriched.warnings,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest src/api/routes/search_test.py -v
```
Expected: PASSED

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
uv run pytest src/ -v --tb=short
```
Expected: all existing tests pass

- [ ] **Step 6: Commit**

```bash
git add src/api/routes/search.py src/api/routes/search_test.py
git commit -m "feat(api): wire OpenAISearchSource and EnrichmentService into search route"
```

---

## Task 8: `/api/explain` endpoint

**Files:**
- Create: `src/api/routes/explain.py`
- Create: `src/api/routes/explain_test.py`
- Modify: `src/api/main.py`

- [ ] **Step 1: Write the failing tests**

Create `src/api/routes/explain_test.py`:

```python
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
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest src/api/routes/explain_test.py -v
```
Expected: 404 or `ImportError`

- [ ] **Step 3: Implement the route**

Create `src/api/routes/explain.py`:

```python
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
        explanation = response.choices[0].message.content
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
```

- [ ] **Step 4: Register router in `src/api/main.py`**

Add to `src/api/main.py` after the existing `search_router` import and include:

```python
from src.api.routes.explain import router as explain_router
```

And in `create_app()`, after `app.include_router(search_router, prefix="/api")`:

```python
app.include_router(explain_router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest src/api/routes/explain_test.py -v
```
Expected: 4 PASSED

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest src/ -v --tb=short
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/api/routes/explain.py src/api/routes/explain_test.py src/api/main.py
git commit -m "feat(api): add POST /api/explain endpoint with token budget and quota handling"
```

---

## Task 9: Frontend — extend domain types

**Files:**
- Modify: `frontend/src/domain/ProductResult.ts`
- Create or modify: `frontend/src/domain/AlternativeResult.ts`

- [ ] **Step 1: Add `AlternativeResult` type**

Create `frontend/src/domain/AlternativeResult.ts`:

```typescript
export interface AlternativeResult {
  title: string;
  reason: string;
  price: number | null;
  currency: string;
  url: string;
  source: string;
}
```

- [ ] **Step 2: Extend `SearchResponse` type in `frontend/src/domain/ProductResult.ts`**

Read the current file first, then add `alternatives`, `enriched`, and `warnings` to the `SearchResponse` interface. The updated interface should be:

```typescript
import { AlternativeResult } from "./AlternativeResult";

export interface SearchResponse {
  query: string;
  query_type: string;
  results: ProductResult[];
  alternatives: AlternativeResult[];
  enriched: boolean;
  warnings: string[];
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/domain/
git commit -m "feat(frontend/domain): add AlternativeResult type and extend SearchResponse"
```

---

## Task 10: Frontend — `ExplainPopup` component

**Files:**
- Create: `frontend/src/ui/ExplainPopup.ts`
- Create: `frontend/src/ui/ExplainPopup.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/ui/ExplainPopup.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ExplainPopup } from "./ExplainPopup";

describe("ExplainPopup", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("renders loading state initially", () => {
    const popup = ExplainPopup({ onClose: () => {} });
    document.body.appendChild(popup);
    expect(document.querySelector(".explain-popup__loading")).not.toBeNull();
  });

  it("renders explanation after setContent is called", () => {
    const popup = ExplainPopup({ onClose: () => {} });
    document.body.appendChild(popup);
    const instance = (popup as any).__explainInstance;
    instance.setContent("This is a great deal.");
    expect(document.querySelector(".explain-popup__content")?.textContent).toContain("This is a great deal.");
  });

  it("renders error state when setError is called", () => {
    const popup = ExplainPopup({ onClose: () => {} });
    document.body.appendChild(popup);
    const instance = (popup as any).__explainInstance;
    instance.setError();
    expect(document.querySelector(".explain-popup__error")).not.toBeNull();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    const popup = ExplainPopup({ onClose });
    document.body.appendChild(popup);
    (document.querySelector(".explain-popup__close") as HTMLElement).click();
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- ExplainPopup --run
```
Expected: `Cannot find module`

- [ ] **Step 3: Implement**

Create `frontend/src/ui/ExplainPopup.ts`:

```typescript
interface ExplainPopupOptions {
  onClose: () => void;
}

interface ExplainPopupInstance {
  setContent: (text: string) => void;
  setError: () => void;
}

export function ExplainPopup({ onClose }: ExplainPopupOptions): HTMLElement {
  const overlay = document.createElement("div");
  overlay.className = "explain-popup__overlay";

  const box = document.createElement("div");
  box.className = "explain-popup__box";

  const closeBtn = document.createElement("button");
  closeBtn.className = "explain-popup__close";
  closeBtn.textContent = "×";
  closeBtn.addEventListener("click", onClose);

  const body = document.createElement("div");
  body.className = "explain-popup__body";

  const loading = document.createElement("div");
  loading.className = "explain-popup__loading";
  loading.textContent = "Analyzing deal…";
  body.appendChild(loading);

  box.appendChild(closeBtn);
  box.appendChild(body);
  overlay.appendChild(box);

  const instance: ExplainPopupInstance = {
    setContent(text: string) {
      body.innerHTML = "";
      const content = document.createElement("p");
      content.className = "explain-popup__content";
      content.textContent = text;
      body.appendChild(content);
    },
    setError() {
      body.innerHTML = "";
      const err = document.createElement("p");
      err.className = "explain-popup__error";
      err.textContent = "Explanation unavailable.";
      body.appendChild(err);
    },
  };

  (overlay as any).__explainInstance = instance;
  return overlay;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npm test -- ExplainPopup --run
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/ExplainPopup.ts frontend/src/ui/ExplainPopup.test.ts
git commit -m "feat(frontend): add ExplainPopup component with loading/content/error states"
```

---

## Task 11: Frontend — `AlternativeCard` and `AlternativesList` components

**Files:**
- Create: `frontend/src/ui/AlternativeCard.ts`
- Create: `frontend/src/ui/AlternativeCard.test.ts`
- Create: `frontend/src/ui/AlternativesList.ts`
- Create: `frontend/src/ui/AlternativesList.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/ui/AlternativeCard.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { AlternativeCard } from "./AlternativeCard";
import { AlternativeResult } from "../domain/AlternativeResult";

describe("AlternativeCard", () => {
  const alt: AlternativeResult = {
    title: "Sony WF-1000XM5",
    reason: "Similar ANC at lower price",
    price: 149.0,
    currency: "EUR",
    url: "https://example.com/sony",
    source: "openai",
  };

  it("renders title", () => {
    const card = AlternativeCard(alt);
    expect(card.textContent).toContain("Sony WF-1000XM5");
  });

  it("renders reason badge", () => {
    const card = AlternativeCard(alt);
    expect(card.querySelector(".alternative-card__reason")?.textContent).toContain("Similar ANC at lower price");
  });

  it("renders price", () => {
    const card = AlternativeCard(alt);
    expect(card.textContent).toContain("149");
  });

  it("renders AI suggestion badge", () => {
    const card = AlternativeCard(alt);
    expect(card.querySelector(".alternative-card__badge")).not.toBeNull();
  });

  it("links to url", () => {
    const card = AlternativeCard(alt);
    const link = card.querySelector("a");
    expect(link?.getAttribute("href")).toBe("https://example.com/sony");
  });
});
```

Create `frontend/src/ui/AlternativesList.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { AlternativesList } from "./AlternativesList";
import { AlternativeResult } from "../domain/AlternativeResult";

describe("AlternativesList", () => {
  const alts: AlternativeResult[] = [
    { title: "Sony WF-1000XM5", reason: "Cheaper", price: 149.0, currency: "EUR", url: "https://a.com", source: "openai" },
    { title: "Bose QuietComfort", reason: "Better ANC", price: 199.0, currency: "EUR", url: "https://b.com", source: "openai" },
  ];

  it("renders all alternatives", () => {
    const list = AlternativesList(alts);
    expect(list.querySelectorAll(".alternative-card").length).toBe(2);
  });

  it("returns hidden element when alternatives is empty", () => {
    const list = AlternativesList([]);
    expect((list as HTMLElement).style.display).toBe("none");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- AlternativeCard AlternativesList --run
```
Expected: `Cannot find module`

- [ ] **Step 3: Implement `AlternativeCard`**

Create `frontend/src/ui/AlternativeCard.ts`:

```typescript
import { AlternativeResult } from "../domain/AlternativeResult";

export function AlternativeCard(alt: AlternativeResult): HTMLElement {
  const card = document.createElement("div");
  card.className = "alternative-card";

  const badge = document.createElement("span");
  badge.className = "alternative-card__badge";
  badge.textContent = "AI suggestion";

  const title = document.createElement("a");
  title.className = "alternative-card__title";
  title.href = alt.url;
  title.target = "_blank";
  title.rel = "noopener noreferrer";
  title.textContent = alt.title;

  const reason = document.createElement("p");
  reason.className = "alternative-card__reason";
  reason.textContent = alt.reason;

  const price = document.createElement("span");
  price.className = "alternative-card__price";
  price.textContent = alt.price !== null ? `${alt.currency} ${alt.price.toFixed(2)}` : "Price unknown";

  card.appendChild(badge);
  card.appendChild(title);
  card.appendChild(reason);
  card.appendChild(price);
  return card;
}
```

- [ ] **Step 4: Implement `AlternativesList`**

Create `frontend/src/ui/AlternativesList.ts`:

```typescript
import { AlternativeResult } from "../domain/AlternativeResult";
import { AlternativeCard } from "./AlternativeCard";

export function AlternativesList(alternatives: AlternativeResult[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "alternatives-list";

  if (alternatives.length === 0) {
    section.style.display = "none";
    return section;
  }

  const heading = document.createElement("h2");
  heading.className = "alternatives-list__heading";
  heading.textContent = "You might also consider";
  section.appendChild(heading);

  alternatives.forEach((alt) => {
    section.appendChild(AlternativeCard(alt));
  });

  return section;
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd frontend && npm test -- AlternativeCard AlternativesList --run
```
Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ui/AlternativeCard.ts frontend/src/ui/AlternativeCard.test.ts \
        frontend/src/ui/AlternativesList.ts frontend/src/ui/AlternativesList.test.ts
git commit -m "feat(frontend): add AlternativeCard and AlternativesList components"
```

---

## Task 12: Frontend — wire "Why is this a good deal?" button and warnings banner

**Files:**
- Modify: `frontend/src/ui/ResultCard.ts`
- Modify: `frontend/src/ui/ResultsList.ts`
- Modify: `frontend/src/application/search.ts`

- [ ] **Step 1: Add explain button to `ResultCard`**

Read `frontend/src/ui/ResultCard.ts` first. Find where the card's action area is rendered and add a button that:
1. Creates an `ExplainPopup` overlay appended to `document.body`
2. Calls `POST /api/explain` with the result's data
3. Calls `instance.setContent(text)` on success or `instance.setError()` on failure

The button addition (insert after the existing "View →" link or at end of card):

```typescript
import { ExplainPopup } from "./ExplainPopup";

// Inside the card rendering function, after existing content:
const explainBtn = document.createElement("button");
explainBtn.className = "result-card__explain-btn";
explainBtn.textContent = "Why is this a good deal?";
explainBtn.addEventListener("click", () => {
  const popup = ExplainPopup({
    onClose: () => document.body.removeChild(popup),
  });
  document.body.appendChild(popup);
  const instance = (popup as any).__explainInstance;

  fetch("/api/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: result.title,
      url: result.url,
      price: result.price,
      query: currentQuery,
    }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.explanation) {
        instance.setContent(data.explanation);
      } else {
        instance.setError();
      }
    })
    .catch(() => instance.setError());
});
card.appendChild(explainBtn);
```

Note: `currentQuery` must be passed into the card render function as a parameter. Update the function signature accordingly and update all call sites in `ResultsList.ts`.

- [ ] **Step 2: Add alternatives section and warnings banner to `ResultsList`**

Read `frontend/src/ui/ResultsList.ts`. After the existing results list, append:

```typescript
import { AlternativesList } from "./AlternativesList";

// After rendering results:
const altSection = AlternativesList(response.alternatives ?? []);
container.appendChild(altSection);

// Warnings banner:
if (response.warnings && response.warnings.length > 0) {
  const banner = document.createElement("div");
  banner.className = "warnings-banner";
  banner.textContent = response.warnings.join(" | ");
  const dismiss = document.createElement("button");
  dismiss.textContent = "×";
  dismiss.addEventListener("click", () => banner.remove());
  banner.appendChild(dismiss);
  container.prepend(banner);
}

// AI enriched badge:
if (response.enriched) {
  const badge = document.createElement("span");
  badge.className = "enriched-badge";
  badge.textContent = "✦ AI-enhanced results";
  container.prepend(badge);
}
```

- [ ] **Step 3: Update `search.ts` to pass new fields**

Read `frontend/src/application/search.ts`. Ensure the `SearchResponse` type from `ProductResult.ts` is used and `alternatives`, `enriched`, `warnings` are passed through to the UI render functions.

- [ ] **Step 4: Run all frontend tests**

```bash
cd frontend && npm test -- --run
```
Expected: all pass

- [ ] **Step 5: Run full backend test suite**

```bash
uv run pytest src/ -v --tb=short
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): wire explain button, alternatives section, warnings banner"
```

---

## Task 13: Manual smoke test

- [ ] **Step 1: Start the app**

```bash
docker-compose up --build
```
Or locally:
```bash
uv run uvicorn src.api.main:app --reload --port 8000
```

- [ ] **Step 2: Search for a product**

```bash
curl -s -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "samsung galaxy buds2 pro"}' | python3 -m json.tool
```

Expected: response includes `alternatives`, `enriched`, `warnings` fields. If `OPENAI_API_KEY` is set, `enriched` should be `true`.

- [ ] **Step 3: Test the explain endpoint**

```bash
curl -s -X POST http://localhost:8000/api/explain \
  -H "Content-Type: application/json" \
  -d '{"title": "Samsung Galaxy Buds2 Pro", "url": "https://bol.com", "price": 169.99, "query": "samsung buds2 pro"}' | python3 -m json.tool
```

Expected: `{"explanation": "...", "warnings": []}`

- [ ] **Step 4: Test without API key**

```bash
OPENAI_API_KEY="" uv run uvicorn src.api.main:app --reload --port 8001
curl -s -X POST http://localhost:8001/api/search -H "Content-Type: application/json" -d '{"query": "test"}' | python3 -m json.tool
```

Expected: `enriched: false`, `alternatives: []`, no warnings.

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -p
git commit -m "fix: smoke test fixes for OpenAI integration"
```
