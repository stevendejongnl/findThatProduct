import asyncio
import logging
from src.application.aggregator import AggregatorService
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery, QueryType
from src.domain.search_source import SearchSource

logger = logging.getLogger(__name__)


class SearchUseCase:
    def __init__(self, sources: list[SearchSource]) -> None:
        self._sources = sources

    async def execute(self, query: SearchQuery) -> list[ProductResult]:
        async def safe_search(source: SearchSource) -> list[ProductResult]:
            try:
                return await source.search(query)
            except Exception as e:
                logger.warning("Source %s failed: %s", source.__class__.__name__, e)
                return []

        results_per_source = await asyncio.gather(*[safe_search(s) for s in self._sources])
        all_results = [r for results in results_per_source for r in results]
        agg_query = "" if query.type == QueryType.EAN else query.raw
        return AggregatorService.aggregate(all_results, query=agg_query)
