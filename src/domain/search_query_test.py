import pytest
from src.domain.search_query import SearchQuery, QueryType


def test_ean_13_detected():
    q = SearchQuery.from_raw("8710447308431")
    assert q.type == QueryType.EAN
    assert q.raw == "8710447308431"


def test_ean_8_detected():
    q = SearchQuery.from_raw("01234565")
    assert q.type == QueryType.EAN


def test_short_number_is_text():
    q = SearchQuery.from_raw("123")
    assert q.type == QueryType.TEXT


def test_product_name_is_text():
    q = SearchQuery.from_raw("peanut butter")
    assert q.type == QueryType.TEXT


def test_mixed_string_is_text():
    q = SearchQuery.from_raw("ABC123")
    assert q.type == QueryType.TEXT


def test_empty_raises():
    with pytest.raises(ValueError, match="Query too short"):
        SearchQuery.from_raw("")


def test_single_char_raises():
    with pytest.raises(ValueError, match="Query too short"):
        SearchQuery.from_raw("a")


def test_ean_14_digits_is_text():
    q = SearchQuery.from_raw("12345678901234")
    assert q.type == QueryType.TEXT
