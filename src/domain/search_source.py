from abc import ABC, abstractmethod
from src.domain.product import ProductResult
from src.domain.search_query import SearchQuery


class SearchSource(ABC):
    @abstractmethod
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        ...
