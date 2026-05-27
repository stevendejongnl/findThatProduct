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

    enrichment = EnrichmentService()
    enriched = await enrichment.enrich(query.raw if query.type != QueryType.EAN else None, raw_results)

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
