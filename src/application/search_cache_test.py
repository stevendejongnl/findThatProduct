import time
import pytest
from src.application.search_cache import SearchCache, _MAX_ENTRIES
from src.application.enrichment import EnrichmentResult
from src.domain.product import ProductResult


def make_enriched(title: str = "Test") -> EnrichmentResult:
    result = ProductResult(title=title, url="https://example.com", source="test", price=9.99, currency="EUR")
    return EnrichmentResult(results=[result], alternatives=[], enriched=False)


def test_miss_returns_none():
    cache = SearchCache(ttl_seconds=60)
    assert cache.get("peanut butter") is None


@pytest.mark.asyncio
async def test_hit_returns_cached_result():
    cache = SearchCache(ttl_seconds=60)
    enriched = make_enriched("Peanut Butter")
    await cache.set("peanut butter", enriched)
    assert cache.get("peanut butter") == enriched


def test_expired_returns_none():
    cache = SearchCache(ttl_seconds=60)
    cache._store["peanut butter"] = (time.monotonic() - 1, make_enriched())
    assert cache.get("peanut butter") is None


@pytest.mark.asyncio
async def test_key_is_case_insensitive():
    cache = SearchCache(ttl_seconds=60)
    await cache.set("Peanut Butter", make_enriched())
    assert cache.get("peanut butter") is not None


@pytest.mark.asyncio
async def test_key_is_stripped():
    cache = SearchCache(ttl_seconds=60)
    await cache.set("  peanut butter  ", make_enriched())
    assert cache.get("peanut butter") is not None


@pytest.mark.asyncio
async def test_evicts_oldest_when_full():
    cache = SearchCache(ttl_seconds=60)
    for i in range(_MAX_ENTRIES):
        await cache.set(f"query {i}", make_enriched(f"Result {i}"))
    await cache.set("query extra", make_enriched("Extra"))
    assert len(cache._store) == _MAX_ENTRIES
    assert cache.get("query 0") is None
    assert cache.get("query extra") is not None
