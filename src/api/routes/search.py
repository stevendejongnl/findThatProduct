from fastapi import APIRouter, HTTPException
from src.api.schemas import SearchRequest, SearchResponse, ProductResultSchema
from src.application.search_use_case import SearchUseCase
from src.domain.search_query import SearchQuery
from src.infrastructure.open_food_facts import OpenFoodFactsSource
from src.infrastructure.upcitemdb import UPCitemdbSource
from src.infrastructure.barcode_monster import BarcodeMonsterSource
from src.infrastructure.duckduckgo import DuckDuckGoSource
from src.infrastructure.bol import BolSource
from src.infrastructure.mediamarkt import MediaMarktSource
from src.infrastructure.coolblue import CoolblueSource
from src.infrastructure.alternate import AlternateSource
from src.infrastructure.tweakers import TweakersSource

router = APIRouter()

SOURCES = [
    BolSource(),
    CoolblueSource(),
    MediaMarktSource(),
    AlternateSource(),
    TweakersSource(),
    OpenFoodFactsSource(),
    UPCitemdbSource(),
    BarcodeMonsterSource(),
    DuckDuckGoSource(),
]


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        query = SearchQuery.from_raw(request.query)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    use_case = SearchUseCase(sources=SOURCES)
    results = await use_case.execute(query)
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
            for r in results
        ],
    )
