# OpenAI Integration — Design Spec
_2026-05-27_

## Purpose

Add OpenAI as both a search source and a post-processing enrichment layer. Goals:
1. **OpenAI web search source** — runs in parallel with existing sources using `gpt-4o-search-preview`, with a token cap.
2. **Enrichment service** — after aggregation, calls GPT-4o once to clean/normalize the result list and generate alternative product suggestions.
3. **Lazy explain endpoint** — per-result "Why is this a good deal?" popup, only called on user request.
4. **Token budget enforcement** — pre-flight token estimation before each OpenAI call; named warnings on quota/rate-limit errors.

---

## Architecture

### New components

```
src/
├── infrastructure/
│   └── openai_search.py          # OpenAISearchSource (implements SearchSource)
├── application/
│   └── enrichment.py             # EnrichmentService
└── api/
    └── routes/
        └── explain.py            # POST /api/explain
```

### Token budget check (shared utility)

```
src/infrastructure/openai_client.py   # Shared OpenAI client factory + token estimator
```

All OpenAI calls go through a single client factory that:
- Returns `None` if `OPENAI_API_KEY` is absent (callers skip gracefully)
- Estimates prompt token count before each call (character-based: `len(prompt) // 4`)
- Raises `TokenBudgetExceeded` if estimate exceeds `OPENAI_TOKEN_BUDGET`
- Catches `openai.RateLimitError` / `openai.AuthenticationError` and re-raises as `OpenAIQuotaError`

Both custom exceptions are caught at the call site and converted to warnings.

---

## Environment Variables

| Var | Default | Notes |
|-----|---------|-------|
| `OPENAI_API_KEY` | — | Required to enable any OpenAI feature. Absent = all OpenAI features silently skipped. |
| `OPENAI_MAX_TOKENS_SEARCH` | `1000` | Token cap for search source call. |
| `OPENAI_MAX_TOKENS_ENRICH` | `1500` | Token cap for enrichment call. |
| `OPENAI_MAX_TOKENS_EXPLAIN` | `300` | Token cap for explain call. |
| `OPENAI_TOKEN_BUDGET` | `2000` | Max tokens allowed per request. Pre-flight check skips call if estimated prompt exceeds this. |

---

## Domain Model Changes

### `AlternativeResult` (new value object)

```python
@dataclass
class AlternativeResult:
    title: str
    reason: str
    price: float | None
    currency: str
    url: str
    source: str = "openai"
```

### `ProductResult` — no changes needed.

---

## API Changes

### `POST /api/search` — extended response

```json
{
  "query": "samsung galaxy buds2 pro",
  "query_type": "text",
  "results": [...],
  "alternatives": [
    {
      "title": "Sony WF-1000XM5",
      "reason": "Similar ANC earbuds at a lower price point",
      "price": 189.00,
      "currency": "EUR",
      "url": "https://...",
      "source": "openai"
    }
  ],
  "enriched": true,
  "warnings": []
}
```

- `alternatives` — empty list when enrichment is disabled/failed/key absent.
- `enriched` — `true` only when enrichment ran successfully.
- `warnings` — list of human-readable strings. Examples:
  - `"OpenAI search skipped: estimated prompt exceeds token budget"`
  - `"OpenAI enrichment skipped: quota exceeded"`

### `POST /api/explain` — new endpoint

Request:
```json
{"title": "Samsung Galaxy Buds2 Pro", "url": "https://...", "price": 169.99, "query": "samsung buds2 pro"}
```

Response:
```json
{
  "explanation": "At €169.99 this is slightly above the average street price of ~€155...",
  "warnings": []
}
```

Error response (OpenAI quota/budget):
```json
{
  "explanation": null,
  "warnings": ["OpenAI explain skipped: quota exceeded"]
}
```

---

## Data Flow

### Search flow

```
POST /api/search
  → SearchQuery.from_raw(query)
    → SearchUseCase.execute(query)
      → asyncio.gather(*all_sources)
          ← OpenAISearchSource:
              estimate prompt tokens
              if > OPENAI_TOKEN_BUDGET → add warning, return []
              call gpt-4o-search-preview (max_tokens=OPENAI_MAX_TOKENS_SEARCH)
              on RateLimitError/AuthError → add warning, return []
        → AggregatorService.aggregate(all_results, query)
          → EnrichmentService.enrich(query, aggregated_results)
              estimate prompt tokens
              if > OPENAI_TOKEN_BUDGET → warnings += [...], return original + []
              call GPT-4o (max_tokens=OPENAI_MAX_TOKENS_ENRICH)
              on error → warnings += [...], return original + []
            → SearchResponse(results, alternatives, enriched, warnings)
              → 200 JSON
```

### Explain flow

```
POST /api/explain
  → estimate prompt tokens
    if > OPENAI_TOKEN_BUDGET → return {explanation: null, warnings: [...]}
    call GPT-4o (max_tokens=OPENAI_MAX_TOKENS_EXPLAIN)
    on RateLimitError/AuthError → return {explanation: null, warnings: [...]}
      → ExplainResponse(explanation, warnings)
        → 200 JSON
```

---

## Failure Modes

| Failure | Behaviour |
|---------|-----------|
| `OPENAI_API_KEY` absent | Source not registered, enrichment/explain skipped, `enriched: false`, no warnings (expected) |
| Prompt exceeds token budget | Call skipped, warning added to response, graceful degradation |
| OpenAI 429 / quota error | Caught as `OpenAIQuotaError`, warning added, graceful degradation |
| Search source throws (any error) | Logged as warning, empty list returned (same as all sources) |
| Enrichment call throws | Original aggregated results returned, `alternatives: []`, `enriched: false`, warning added |
| Explain call throws | `explanation: null`, warning in response, frontend shows "Explanation unavailable" |

---

## New Pydantic Schemas

```python
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

---

## Frontend Changes

### New components

| Component | Purpose |
|-----------|---------|
| `AlternativeCard.ts` | Single alternative suggestion card with reason badge |
| `AlternativesList.ts` | Section below main results, hidden when `alternatives` is empty |
| `ExplainPopup.ts` | Modal overlay: loading → explanation text, or error state |

### UI additions

- **Alternatives section** — below main results list, same card style + "AI suggestion" badge + `reason` as subtitle.
- **"Why is this a good deal?" button** — on each result card. Opens `ExplainPopup`, fires `POST /api/explain`, shows loading spinner → explanation text.
- **"AI enriched" badge** — small indicator in results header when `enriched: true`.
- **Warnings banner** — dismissible banner at top of results when `warnings.length > 0`.

### No new npm dependencies. Vanilla TS, same pattern as existing components.

---

## Testing Strategy

### Backend

| Unit | What's tested |
|------|--------------|
| `OpenAISearchSource` | Returns parsed results; returns `[]` on API error; token cap in request; skips when key absent |
| `EnrichmentService` | Returns cleaned results + alternatives; returns originals on error; `enriched: False` when key absent |
| `openai_client.py` | `TokenBudgetExceeded` raised when estimate exceeds budget; `OpenAIQuotaError` on 429 |
| `/api/explain` route | Returns explanation; returns `warnings` on quota error; 200 always (no 500s) |

All OpenAI calls mocked. `OPENAI_API_KEY` absence tested explicitly.

### Frontend (Vitest)

| Component | What's tested |
|-----------|--------------|
| `AlternativesList` | Renders when alternatives present; hidden when empty |
| `AlternativeCard` | Renders title, reason badge, price |
| `ExplainPopup` | Shows loading on open; shows explanation on success; shows error state on failed fetch |
| Warnings banner | Renders when warnings present; hidden when empty; dismissible |

---

## File Structure (additions only)

```
src/
├── domain/
│   └── alternative_result.py        # AlternativeResult value object
├── infrastructure/
│   ├── openai_client.py             # Client factory, token estimator, custom exceptions
│   └── openai_search.py             # OpenAISearchSource
│   └── openai_search_test.py
├── application/
│   └── enrichment.py                # EnrichmentService
│   └── enrichment_test.py
└── api/
    ├── routes/
    │   └── explain.py               # POST /api/explain
    │   └── explain_test.py
    └── schemas.py                   # Extended with new schemas

frontend/src/
└── ui/
    ├── AlternativeCard.ts + AlternativeCard.test.ts
    ├── AlternativesList.ts + AlternativesList.test.ts
    └── ExplainPopup.ts + ExplainPopup.test.ts
```
