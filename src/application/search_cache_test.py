import time
import pytest
from src.application.search_cache import SearchCache
from src.domain.product import ProductResult


def make_result(title: str = "Test") -> ProductResult:
    return ProductResult(title=title, url="https://example.com", source="test", price=9.99, currency="EUR")


def test_miss_returns_none():
    cache = SearchCache(ttl_seconds=60)
    assert cache.get("peanut butter") is None


@pytest.mark.asyncio
async def test_hit_returns_cached_results():
    cache = SearchCache(ttl_seconds=60)
    results = [make_result("Peanut Butter")]
    await cache.set("peanut butter", results)
    assert cache.get("peanut butter") == results


def test_expired_returns_none():
    from unittest.mock import patch
    cache = SearchCache(ttl_seconds=60)
    cache._store["peanut butter"] = (time.monotonic() - 1, [make_result()])  # already expired
    assert cache.get("peanut butter") is None


@pytest.mark.asyncio
async def test_key_is_case_insensitive():
    cache = SearchCache(ttl_seconds=60)
    await cache.set("Peanut Butter", [make_result()])
    assert cache.get("peanut butter") is not None


@pytest.mark.asyncio
async def test_key_is_stripped():
    cache = SearchCache(ttl_seconds=60)
    await cache.set("  peanut butter  ", [make_result()])
    assert cache.get("peanut butter") is not None


@pytest.mark.asyncio
async def test_evicts_oldest_when_full():
    cache = SearchCache(ttl_seconds=60)
    # Fill to _MAX_ENTRIES
    from src.application.search_cache import _MAX_ENTRIES
    for i in range(_MAX_ENTRIES):
        await cache.set(f"query {i}", [make_result(f"Result {i}")])
    # Adding one more should evict "query 0"
    await cache.set("query extra", [make_result("Extra")])
    assert len(cache._store) == _MAX_ENTRIES
    assert cache.get("query 0") is None
    assert cache.get("query extra") is not None
