# Search Cache + SSE Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 1-hour in-memory search cache and a global server-side queue that streams live position updates to the browser via SSE while the user waits.

**Architecture:** A module-level `SearchCache` (TTL dict) and `asyncio.Semaphore(1)` live in `src/api/routes/search.py`. The existing `POST /api/search` is replaced by `GET /api/search/stream?q=…` which returns an SSE stream: it emits `queued` events (with position) while waiting, then emits a single `result` event with the full JSON payload. The frontend replaces its `post()` call with an `EventSource` connection, updating `setStatus()` on queue events and rendering results on the `result` event.

**Tech Stack:** FastAPI `StreamingResponse`, `asyncio.Semaphore`, vanilla `EventSource` API in TypeScript, Vitest + happy-dom for frontend tests.

---

## File Structure

**New files:**
- `src/application/search_cache.py` — `SearchCache` class: TTL-based in-memory cache keyed by normalized query string
- `src/application/search_cache_test.py` — tests for cache hit/miss/expiry

**Modified files:**
- `src/api/routes/search.py` — add `Semaphore(1)`, cache lookup, SSE streaming endpoint `GET /api/search/stream`; keep `POST /api/search` for backwards compat (returns cached or queued result synchronously)
- `src/api/routes/search_test.py` — add tests for cache hit, queue position header
- `frontend/src/application/search.ts` — replace `post()` with `EventSource`-based `searchProducts()` that calls back on queue position and result
- `frontend/src/application/search.test.ts` — update tests for new SSE-based API
- `frontend/src/main.ts` — pass `onQueuePosition` callback to `searchProducts()`, update `setStatus()` with queue message

---

### Task 1: SearchCache — TTL in-memory cache

**Files:**
- Create: `src/application/search_cache.py`
- Create: `src/application/search_cache_test.py`

- [ ] **Step 1: Write the failing tests**

```python
# src/application/search_cache_test.py
import time
import pytest
from src.application.search_cache import SearchCache
from src.domain.product import ProductResult


def make_result(title: str = "Test") -> ProductResult:
    return ProductResult(title=title, url="https://example.com", source="test", price=9.99, currency="EUR")


def test_miss_returns_none():
    cache = SearchCache(ttl_seconds=60)
    assert cache.get("peanut butter") is None


def test_hit_returns_cached_results():
    cache = SearchCache(ttl_seconds=60)
    results = [make_result("Peanut Butter")]
    cache.set("peanut butter", results)
    assert cache.get("peanut butter") == results


def test_expired_returns_none():
    cache = SearchCache(ttl_seconds=0)  # expires immediately
    cache.set("peanut butter", [make_result()])
    time.sleep(0.01)
    assert cache.get("peanut butter") is None


def test_key_is_case_insensitive():
    cache = SearchCache(ttl_seconds=60)
    cache.set("Peanut Butter", [make_result()])
    assert cache.get("peanut butter") is not None


def test_key_is_stripped():
    cache = SearchCache(ttl_seconds=60)
    cache.set("  peanut butter  ", [make_result()])
    assert cache.get("peanut butter") is not None
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest src/application/search_cache_test.py -q
```
Expected: `ModuleNotFoundError: No module named 'src.application.search_cache'`

- [ ] **Step 3: Implement `src/application/search_cache.py`**

```python
import time
from src.domain.product import ProductResult


class SearchCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, list[ProductResult]]] = {}

    def _normalize(self, query: str) -> str:
        return query.strip().lower()

    def get(self, query: str) -> list[ProductResult] | None:
        key = self._normalize(query)
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, results = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return results

    def set(self, query: str, results: list[ProductResult]) -> None:
        key = self._normalize(query)
        self._store[key] = (time.monotonic() + self._ttl, results)
```

- [ ] **Step 4: Run to verify tests pass**

```bash
uv run pytest src/application/search_cache_test.py -q
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/application/search_cache.py src/application/search_cache_test.py
git commit -m "feat(cache): add TTL in-memory search cache"
```

---

### Task 2: SSE streaming search endpoint

**Files:**
- Modify: `src/api/routes/search.py`
- Modify: `src/api/routes/search_test.py`

The new endpoint is `GET /api/search/stream?q=<query>`. It:
1. Checks the cache — if hit, immediately emits `event: result\ndata: <json>\n\n` and closes.
2. If miss, acquires `Semaphore(1)`. While waiting for the semaphore, emits `event: queued\ndata: {"position": N}\n\n` every second.
3. Once acquired, runs the search + enrichment, stores in cache, emits `event: result\ndata: <json>\n\n`, releases semaphore.

The queue position is tracked with a module-level counter.

- [ ] **Step 1: Write the failing tests**

```python
# Add to src/api/routes/search_test.py

def test_stream_cache_hit_returns_result_immediately(client):
    """Cache hit: SSE stream emits a single result event with no queued events."""
    from src.api.routes import search as search_module
    from src.domain.product import ProductResult

    cached = [ProductResult(title="Cached", url="https://x.com", source="test", price=1.0, currency="EUR")]
    search_module.CACHE.set("peanut butter", cached)

    resp = client.get("/api/search/stream?q=peanut+butter")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    result_events = [e for e in events if e["event"] == "result"]
    queued_events = [e for e in events if e["event"] == "queued"]

    assert len(result_events) == 1
    assert len(queued_events) == 0
    data = json.loads(result_events[0]["data"])
    assert data["query"] == "peanut butter"
    assert len(data["results"]) == 1


def test_stream_missing_query_returns_422(client):
    resp = client.get("/api/search/stream")
    assert resp.status_code == 422


def _parse_sse(text: str) -> list[dict]:
    """Parse SSE text into list of {event, data} dicts."""
    events = []
    current: dict = {}
    for line in text.splitlines():
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = line[len("data:"):].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events
```

Also add `import json` to the top of `src/api/routes/search_test.py`.

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest src/api/routes/search_test.py::test_stream_cache_hit_returns_result_immediately src/api/routes/search_test.py::test_stream_missing_query_returns_422 -q
```
Expected: FAIL — `404 Not Found` (endpoint doesn't exist yet)

- [ ] **Step 3: Implement the SSE endpoint in `src/api/routes/search.py`**

Add these imports at the top:
```python
import asyncio
import json
import time
from fastapi import Query
from fastapi.responses import StreamingResponse
from src.application.search_cache import SearchCache
```

Add module-level state after `SOURCES = _build_sources()`:
```python
CACHE = SearchCache(ttl_seconds=int(os.getenv("SEARCH_CACHE_TTL", "3600")))
_SEMAPHORE = asyncio.Semaphore(1)
_QUEUE_COUNTER = 0  # number of requests currently waiting for the semaphore
```

Add helper to build `SearchResponse` from enrichment result:
```python
def _build_response(query: SearchQuery, enriched) -> SearchResponse:
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

Add the SSE endpoint:
```python
@router.get("/search/stream")
async def search_stream(q: str = Query(..., min_length=1)) -> StreamingResponse:
    try:
        query = SearchQuery.from_raw(q)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    async def generate():
        global _QUEUE_COUNTER

        # Cache hit — emit result immediately
        cached = CACHE.get(query.raw)
        if cached is not None:
            enrichment = EnrichmentService()
            from src.application.enrichment import EnrichmentResult
            fake_enriched = EnrichmentResult(results=cached, enriched=False)
            response = SearchResponse(
                query=query.raw,
                query_type=query.type.value,
                results=[
                    ProductResultSchema(
                        title=r.title, price=r.price, currency=r.currency,
                        url=r.url, source=r.source, image_url=r.image_url, ean=r.ean,
                    )
                    for r in cached
                ],
            )
            yield f"event: result\ndata: {response.model_dump_json()}\n\n"
            return

        # Queue — emit position while waiting for semaphore
        _QUEUE_COUNTER += 1
        position = _QUEUE_COUNTER
        try:
            while _SEMAPHORE.locked():
                yield f"event: queued\ndata: {json.dumps({'position': position})}\n\n"
                await asyncio.sleep(1)

            async with _SEMAPHORE:
                _QUEUE_COUNTER -= 1
                use_case = SearchUseCase(sources=SOURCES)
                raw_results = await use_case.execute(query)
                CACHE.set(query.raw, raw_results)

                enrichment = EnrichmentService()
                enriched = await enrichment.enrich(
                    query.raw if query.type != QueryType.EAN else None, raw_results
                )
                response = _build_response(query, enriched)
                yield f"event: result\ndata: {response.model_dump_json()}\n\n"
        except Exception:
            _QUEUE_COUNTER -= 1
            raise

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })
```

Also refactor the existing `POST /api/search` to use `_build_response()` to avoid duplication:
```python
@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        query = SearchQuery.from_raw(request.query)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    cached = CACHE.get(query.raw)
    if cached is not None:
        from src.application.enrichment import EnrichmentResult
        fake_enriched = EnrichmentResult(results=cached, enriched=False)
        return _build_response(query, fake_enriched)

    use_case = SearchUseCase(sources=SOURCES)
    raw_results = await use_case.execute(query)
    CACHE.set(query.raw, raw_results)

    enrichment = EnrichmentService()
    enriched = await enrichment.enrich(
        query.raw if query.type != QueryType.EAN else None, raw_results
    )
    return _build_response(query, enriched)
```

- [ ] **Step 4: Run to verify tests pass**

```bash
uv run pytest src/api/routes/search_test.py -q
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/search.py src/api/routes/search_test.py
git commit -m "feat(search): add SSE stream endpoint with queue position and cache lookup"
```

---

### Task 3: Frontend — SSE-based searchProducts

**Files:**
- Modify: `frontend/src/application/search.ts`
- Modify: `frontend/src/application/search.test.ts`

Replace the `post()` call with an `EventSource`-style fetch using the native `fetch` + `ReadableStream` API (so it works in the same origin and in tests with `vi.stubGlobal("fetch", ...)`).

The new signature:
```ts
export async function searchProducts(
  raw: string,
  onQueuePosition?: (position: number) => void
): Promise<SearchResponse>
```

It opens a `fetch` to `GET /api/search/stream?q=<query>`, reads the SSE stream line by line, calls `onQueuePosition(n)` on `queued` events, and resolves with the parsed `SearchResponse` on the `result` event.

- [ ] **Step 1: Write the failing tests**

Replace the content of `frontend/src/application/search.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchProducts } from "./search";

beforeEach(() => {
  vi.restoreAllMocks();
});

function makeSseStream(events: Array<{ event: string; data: string }>): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const text = events.map(e => `event: ${e.event}\ndata: ${e.data}\n\n`).join("");
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
}

const mockResponse = {
  query: "peanut butter",
  query_type: "text",
  results: [{ title: "P", price: 4.99, currency: "EUR", url: "https://x.com", source: "test", image_url: null, ean: null }],
  alternatives: [],
  enriched: false,
  warnings: [],
};

describe("searchProducts", () => {
  it("resolves with SearchResponse on result event", async () => {
    vi.stubGlobal("fetch", () =>
      Promise.resolve({
        ok: true,
        body: makeSseStream([{ event: "result", data: JSON.stringify(mockResponse) }]),
      })
    );
    const result = await searchProducts("peanut butter");
    expect(result.query).toBe("peanut butter");
    expect(result.results).toHaveLength(1);
  });

  it("calls onQueuePosition for queued events", async () => {
    const positions: number[] = [];
    vi.stubGlobal("fetch", () =>
      Promise.resolve({
        ok: true,
        body: makeSseStream([
          { event: "queued", data: JSON.stringify({ position: 2 }) },
          { event: "queued", data: JSON.stringify({ position: 1 }) },
          { event: "result", data: JSON.stringify(mockResponse) },
        ]),
      })
    );
    await searchProducts("peanut butter", (pos) => positions.push(pos));
    expect(positions).toEqual([2, 1]);
  });

  it("throws on HTTP error", async () => {
    vi.stubGlobal("fetch", () => Promise.resolve({ ok: false, status: 422, body: null }));
    await expect(searchProducts("a")).rejects.toThrow("422");
  });

  it("throws on short query (client-side guard)", async () => {
    await expect(searchProducts("a")).rejects.toThrow();
  });

  it("throws if stream ends without result event", async () => {
    vi.stubGlobal("fetch", () =>
      Promise.resolve({
        ok: true,
        body: makeSseStream([{ event: "queued", data: '{"position":1}' }]),
      })
    );
    await expect(searchProducts("peanut butter")).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /home/stevendejong/workspace/personal/home-automation/findThatProduct/frontend && npm test -- --run search.test
```
Expected: multiple failures

- [ ] **Step 3: Implement the new `search.ts`**

```ts
import { createSearchQuery } from "../domain/SearchQuery";
import { ProductResult } from "../domain/ProductResult";
import { AlternativeResult } from "../domain/AlternativeResult";

export interface SearchResponse {
  query: string;
  query_type: string;
  results: ProductResult[];
  alternatives: AlternativeResult[];
  enriched: boolean;
  warnings: string[];
}

export async function searchProducts(
  raw: string,
  onQueuePosition?: (position: number) => void
): Promise<SearchResponse> {
  const query = createSearchQuery(raw);
  const url = `/api/search/stream?q=${encodeURIComponent(query.raw)}`;

  const resp = await fetch(url);
  if (!resp.ok) throw new Error(String(resp.status));
  if (!resp.body) throw new Error("No response body");

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        const data = line.slice("data:".length).trim();
        if (currentEvent === "queued") {
          const parsed = JSON.parse(data) as { position: number };
          onQueuePosition?.(parsed.position);
        } else if (currentEvent === "result") {
          return JSON.parse(data) as SearchResponse;
        }
        currentEvent = "";
      }
    }
  }

  throw new Error("Stream ended without result");
}
```

- [ ] **Step 4: Run to verify tests pass**

```bash
cd /home/stevendejong/workspace/personal/home-automation/findThatProduct/frontend && npm test -- --run search.test
```
Expected: 5 passed

- [ ] **Step 5: Run full frontend test suite**

```bash
cd /home/stevendejong/workspace/personal/home-automation/findThatProduct/frontend && npm test -- --run
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add frontend/src/application/search.ts frontend/src/application/search.test.ts
git commit -m "feat(frontend): switch searchProducts to SSE stream with queue position callback"
```

---

### Task 4: Frontend — wire queue position into main.ts

**Files:**
- Modify: `frontend/src/main.ts`

Pass `onQueuePosition` to `searchProducts()`. Update the `setStatus()` call to show queue position while waiting.

- [ ] **Step 1: Update `handleSearch` in `frontend/src/main.ts`**

Replace:
```ts
    setStatus("Searching…");

    let response;
    try {
      response = await searchProducts(query);
    } catch (e) {
```

With:
```ts
    setStatus("Searching…");

    let response;
    try {
      response = await searchProducts(query, (position) => {
        setStatus(`Searching… (queue position: ${position})`);
      });
    } catch (e) {
```

- [ ] **Step 2: Run full test suite to check no regressions**

```bash
cd /home/stevendejong/workspace/personal/home-automation/findThatProduct/frontend && npm test -- --run
```
Expected: all pass

- [ ] **Step 3: Run backend tests**

```bash
cd /home/stevendejong/workspace/personal/home-automation/findThatProduct && uv run pytest -q
```
Expected: all pass (2 DDG failures are pre-existing and unrelated)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.ts
git commit -m "feat(frontend): show queue position in status bar while waiting for search"
```

---

## Self-Review

**Spec coverage:**
- ✅ 1-hour TTL in-memory cache — Task 1 (`SearchCache`) + Task 2 (cache lookup in both endpoints)
- ✅ Global server-side queue (one search at a time) — Task 2 (`Semaphore(1)`)
- ✅ Live queue position via SSE — Task 2 (`event: queued`) + Task 3 (frontend reads `queued` events) + Task 4 (status bar update)
- ✅ Cache TTL configurable via `SEARCH_CACHE_TTL` env var — Task 2

**Placeholder scan:** None found. All steps have complete code.

**Type consistency:**
- `SearchCache.get()` returns `list[ProductResult] | None` — consistent across Task 1 and Task 2
- `SearchResponse` interface unchanged — Tasks 3-4 use same type
- `onQueuePosition?: (position: number) => void` — consistent between Task 3 definition and Task 4 call site
- `_build_response(query, enriched)` — defined in Task 2, used in both POST and GET handlers
