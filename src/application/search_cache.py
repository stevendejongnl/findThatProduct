import asyncio
import time
from src.application.enrichment import EnrichmentResult

_MAX_ENTRIES = 500


class SearchCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, EnrichmentResult]] = {}
        self._lock = asyncio.Lock()

    def _normalize(self, query: str) -> str:
        return query.strip().lower()

    def get(self, query: str) -> EnrichmentResult | None:
        key = self._normalize(query)
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, result = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return result

    async def set(self, query: str, result: EnrichmentResult) -> None:
        key = self._normalize(query)
        async with self._lock:
            if len(self._store) >= _MAX_ENTRIES:
                oldest = next(iter(self._store))
                del self._store[oldest]
            self._store[key] = (time.monotonic() + self._ttl, result)
