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
