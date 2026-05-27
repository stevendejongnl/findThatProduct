import asyncio
import json
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from src.api.schemas import SearchRequest, SearchResponse, ProductResultSchema, AlternativeSchema
from src.application.enrichment import EnrichmentService, EnrichmentResult
from src.application.search_cache import SearchCache
from src.application.search_use_case import SearchUseCase
from src.domain.product import ProductResult
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
        BolSource(), CoolblueSource(), MediaMarktSource(), AlternateSource(),
        AmazonNLSource(), TweakersSource(), OpenFoodFactsSource(),
        UPCitemdbSource(), BarcodeMonsterSource(), DuckDuckGoSource(),
    ]
    if os.getenv("OPENAI_API_KEY"):
        sources.append(OpenAISearchSource())
    return sources


SOURCES = _build_sources()
CACHE = SearchCache(ttl_seconds=int(os.getenv("SEARCH_CACHE_TTL", "3600")))
_SEMAPHORE = asyncio.Semaphore(1)
_waiting: int = 0


def _build_response(query: SearchQuery, enriched: EnrichmentResult) -> SearchResponse:
    return SearchResponse(
        query=query.raw,
        query_type=query.type.value,
        results=[
            ProductResultSchema(
                title=r.title, price=r.price, currency=r.currency,
                url=r.url, source=r.source, image_url=r.image_url, ean=r.ean,
            )
            for r in enriched.results
        ],
        alternatives=[
            AlternativeSchema(
                title=a.title, reason=a.reason, price=a.price,
                currency=a.currency, url=a.url, source=a.source,
            )
            for a in enriched.alternatives
        ],
        enriched=enriched.enriched,
        warnings=enriched.warnings,
    )


async def _run_search(query: SearchQuery) -> EnrichmentResult:
    """Run search + enrichment, store raw results in cache."""
    use_case = SearchUseCase(sources=SOURCES)
    raw_results = await use_case.execute(query)
    await CACHE.set(query.raw, raw_results)
    enrichment = EnrichmentService()
    return await enrichment.enrich(
        query.raw if query.type != QueryType.EAN else None, raw_results
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        query = SearchQuery.from_raw(request.query)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    cached = CACHE.get(query.raw)
    if cached is not None:
        return _build_response(query, EnrichmentResult(results=cached, enriched=False))

    async with _SEMAPHORE:
        enriched = await _run_search(query)
    return _build_response(query, enriched)


@router.get("/search/stream")
async def search_stream(q: str = Query(..., min_length=1)) -> StreamingResponse:
    try:
        query = SearchQuery.from_raw(q)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    async def generate():
        global _waiting

        cached = CACHE.get(query.raw)
        if cached is not None:
            response = _build_response(query, EnrichmentResult(results=cached, enriched=False))
            yield f"event: result\ndata: {response.model_dump_json()}\n\n"
            return

        _waiting += 1
        try:
            while _SEMAPHORE.locked():
                yield f"event: queued\ndata: {json.dumps({'position': _waiting})}\n\n"
                await asyncio.sleep(1)

            async with _SEMAPHORE:
                _waiting -= 1
                enriched = await _run_search(query)
                response = _build_response(query, enriched)
                yield f"event: result\ndata: {response.model_dump_json()}\n\n"
        except Exception:
            _waiting = max(0, _waiting - 1)
            raise

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
