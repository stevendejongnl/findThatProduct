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
