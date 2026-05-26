# findThatProduct — Design Spec
_2026-05-26_

## Purpose

Personal price comparison tool. Input: EAN barcode or product name. Output: ranked list of results from multiple sources, sorted by price ascending. Goal: find the best-priced product fast.

---

## Architecture

### Overview

Two independently deployable images: backend (FastAPI) and frontend (Nginx + static TS build). No secrets baked into images. Config injected at runtime via env vars.

```
[Browser] ──HTTP──► [Frontend: Nginx]
                         │
                    [API: FastAPI]
                         │
              ┌──────────┼──────────┐
         [OpenFoodFacts] [UPCitemdb] [barcode.monster] [DuckDuckGo scrape]
```

### DDD Layers (backend)

```
src/
├── domain/           # Entities, value objects, interfaces — no framework deps
│   ├── product.py          # ProductResult entity
│   ├── search_query.py     # SearchQuery value object (validates EAN vs text)
│   └── search_source.py    # SearchSource interface (ABC)
├── application/      # Use cases — orchestrates domain + infrastructure
│   ├── search_use_case.py  # SearchUseCase: parallel query + aggregate
│   └── aggregator.py       # Deduplicate, normalize, rank by price
├── infrastructure/   # External adapters implementing SearchSource
│   ├── open_food_facts.py
│   ├── upcitemdb.py
│   ├── barcode_monster.py
│   └── duckduckgo.py
└── api/              # FastAPI routes + Pydantic schemas
    ├── main.py
    ├── routes/
    │   └── search.py
    └── schemas.py
```

### DDD Layers (frontend)

```
frontend/src/
├── domain/           # Types and interfaces
│   ├── ProductResult.ts
│   └── SearchQuery.ts
├── application/      # Search orchestration, state
│   └── search.ts
├── infrastructure/   # API client (fetch wrapper)
│   └── apiClient.ts
└── ui/               # Components (pure TS functions, no framework)
    ├── SearchBar.ts
    ├── ResultsList.ts
    └── ResultCard.ts
```

---

## Domain Model

### SearchQuery (value object)

- `raw: str` — original user input
- `type: "ean" | "text"` — detected automatically
- EAN: 8 or 13 digit numeric string (validated)
- text: anything else, min 2 chars

### ProductResult (entity)

```python
@dataclass
class ProductResult:
    title: str
    price: float | None
    currency: str        # default "EUR"
    url: str
    source: str          # e.g. "open_food_facts"
    image_url: str | None = None
    ean: str | None = None
```

### SearchSource (interface)

```python
class SearchSource(ABC):
    @abstractmethod
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        ...
```

Adding a new source = implement this interface + register in DI. No other changes.

---

## Data Flow

```
User input
  → POST /api/search {query: "8710447308431"}
    → SearchQuery.from_raw("8710447308431") → type=ean
      → SearchUseCase.execute(query)
        → asyncio.gather(*[source.search(query) for source in sources])
          → AggregatorService.aggregate(all_results)
            → deduplicate by url
            → filter: price not None first, None last
            → sort by price ascending
              → SearchResponse(results=[...])
                → 200 JSON
                  → Frontend renders ResultsList
```

Error handling: each source wrapped in try/except. Failure = log warning + empty list. Never propagates to caller. Partial results always returned.

---

## API

### `POST /api/search`

Request:
```json
{"query": "8710447308431"}
```

Response:
```json
{
  "query": "8710447308431",
  "query_type": "ean",
  "results": [
    {
      "title": "Product Name",
      "price": 4.99,
      "currency": "EUR",
      "url": "https://...",
      "source": "open_food_facts",
      "image_url": "https://...",
      "ean": "8710447308431"
    }
  ]
}
```

### `GET /healthz`

Returns `{"status": "ok"}`. Used by k8s liveness/readiness probes.

---

## Search Sources (Phase 1)

| Source | Type | EAN | Text | Notes |
|--------|------|-----|------|-------|
| Open Food Facts | Free API | ✓ | ✗ | Food products, prices rare |
| UPCitemdb | Free API (500/day) | ✓ | ✓ | General products |
| barcode.monster | Free API | ✓ | ✗ | Barcode fallback |
| DuckDuckGo scrape | Scrape | ✓ | ✓ | Price extraction brittle, best-effort |

Phase 2: add API key config → SerpAPI, Bol.com, Amazon affiliate.

---

## Frontend

### Stack

- Vite + TypeScript
- Vanilla TS (no React/Vue/Svelte)
- Vitest for unit tests
- No inline JS or CSS
- External CSS only, mobile-first

### npm deps

```json
{
  "devDependencies": {
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vitest": "^1.6.0"
  }
}
```

Zero runtime npm deps.

### UI Layout (mobile-first)

```
┌─────────────────────────────┐
│  findThatProduct            │
│  ┌──────────────────────┐   │
│  │ EAN or product name  │   │
│  └──────────────────────┘   │
│  [Search]                   │
├─────────────────────────────┤
│  ● Product Name       €4.99 │
│    source: open_food_facts  │
│    [View →]                 │
├─────────────────────────────┤
│  ● Product Name       €6.50 │
│    source: upcitemdb        │
│    [View →]                 │
└─────────────────────────────┘
```

---

## Testing Strategy

BDD/TDD, red-green-refactor. Tests co-located next to source files.

```
src/domain/product.py
src/domain/product_test.py

src/application/search_use_case.py
src/application/search_use_case_test.py

src/infrastructure/open_food_facts.py
src/infrastructure/open_food_facts_test.py

frontend/src/application/search.ts
frontend/src/application/search.test.ts
```

### Example BDD scenarios

```gherkin
Scenario: Search by valid EAN
  Given user enters EAN "8710447308431"
  When search executes
  Then results are sorted by price ascending
  And each result has a title and source

Scenario: Search by product name
  Given user enters "peanut butter"
  When search executes
  Then results contain items from at least one source

Scenario: Source failure is isolated
  Given the UPCitemdb adapter raises an exception
  When search executes
  Then other source results are still returned
  And no error is raised to the caller

Scenario: Invalid EAN falls back to text search
  Given user enters "123"
  When SearchQuery is created
  Then query type is "text"
```

### pytest config

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--cov=src --cov-report=term-missing"
testpaths = ["src"]
python_files = ["*_test.py"]
python_functions = ["test_*"]
```

---

## Docker

### Multi-stage Dockerfile

```
Stage 1: frontend (node:20-slim)
  → npm ci → vite build → /dist

Stage 2: app (python:3.12-slim)
  → uv sync --no-dev --frozen
  → COPY src/
  → COPY --from=frontend /dist → app/static/
  → CMD uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

No secrets baked in. All config via env vars.

### Environment variables

| Var | Default | Notes |
|-----|---------|-------|
| `PORT` | `8000` | FastAPI port |
| `LOG_LEVEL` | `info` | uvicorn log level |
| `ALLOWED_ORIGINS` | `*` | CORS origins |

Phase 2 additions (optional, not required for phase 1):
- `SOURCE_SERPAPI_KEY`
- `SOURCE_BOL_KEY`

---

## Kubernetes

```
k8s/
├── example/                      # committed, safe to share
│   ├── deployment.yaml           # Keel annotations, ghcr image, envFrom secretRef
│   ├── service.yaml              # ClusterIP, port 80 → 8000
│   ├── ingress.yaml              # nginx ingress
│   ├── namespace.yaml
│   └── secrets/
│       └── findthatproduct-secrets.example.yaml
└── .gitignore                    # ignores k8s/*.yaml (personal configs live outside example/)
```

Keel annotations on deployment:
```yaml
annotations:
  keel.sh/policy: minor
  keel.sh/trigger: poll
  keel.sh/pollSchedule: "@every 5m"
```

Image: `ghcr.io/stevendejongnl/findthatproduct:v1.0.0`

---

## CI/CD & Semantic Release

Follows changewatch pattern exactly:

```yaml
jobs:
  test → release (semantic-release) → build & push (GHCR)
```

- Conventional commits → semantic-release → GitHub release
- Tags: `vX.Y.Z` on GHCR
- Keel polls GHCR every 5m → auto-deploys minor/patch

`.releaserc` or `package.json` semantic-release config committed to repo.

---

## File Structure (final)

```
findThatProduct/
├── src/
│   ├── domain/
│   │   ├── product.py + product_test.py
│   │   ├── search_query.py + search_query_test.py
│   │   └── search_source.py
│   ├── application/
│   │   ├── search_use_case.py + search_use_case_test.py
│   │   └── aggregator.py + aggregator_test.py
│   ├── infrastructure/
│   │   ├── open_food_facts.py + open_food_facts_test.py
│   │   ├── upcitemdb.py + upcitemdb_test.py
│   │   ├── barcode_monster.py + barcode_monster_test.py
│   │   └── duckduckgo.py + duckduckgo_test.py
│   └── api/
│       ├── main.py + main_test.py
│       ├── routes/
│       │   └── search.py + search_test.py
│       └── schemas.py
├── frontend/
│   ├── src/
│   │   ├── domain/
│   │   │   ├── ProductResult.ts + ProductResult.test.ts
│   │   │   └── SearchQuery.ts + SearchQuery.test.ts
│   │   ├── application/
│   │   │   └── search.ts + search.test.ts
│   │   ├── infrastructure/
│   │   │   └── apiClient.ts + apiClient.test.ts
│   │   └── ui/
│   │       ├── SearchBar.ts + SearchBar.test.ts
│   │       ├── ResultsList.ts + ResultsList.test.ts
│   │       └── ResultCard.ts + ResultCard.test.ts
│   ├── index.html
│   ├── style.css
│   ├── vite.config.ts
│   └── package.json
├── k8s/
│   └── example/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── ingress.yaml
│       ├── namespace.yaml
│       └── secrets/
│           └── findthatproduct-secrets.example.yaml
├── .github/
│   └── workflows/
│       └── ci.yml
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .releaserc.json
├── .gitignore
└── README.md
```
