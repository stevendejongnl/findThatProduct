from src.domain.product import ProductResult


def test_product_result_minimal():
    p = ProductResult(title="Test", url="https://example.com", source="test")
    assert p.title == "Test"
    assert p.price is None
    assert p.currency == "EUR"
    assert p.url == "https://example.com"
    assert p.source == "test"
    assert p.image_url is None
    assert p.ean is None


def test_product_result_with_price():
    p = ProductResult(title="Test", price=4.99, currency="EUR", url="https://example.com", source="test")
    assert p.price == 4.99


def test_product_result_with_all_fields():
    p = ProductResult(
        title="Peanut Butter",
        price=3.49,
        currency="EUR",
        url="https://example.com/peanut",
        source="open_food_facts",
        image_url="https://example.com/img.jpg",
        ean="8710447308431",
    )
    assert p.ean == "8710447308431"
    assert p.image_url == "https://example.com/img.jpg"
