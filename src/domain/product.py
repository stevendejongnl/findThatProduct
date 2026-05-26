from dataclasses import dataclass


@dataclass
class ProductResult:
    title: str
    url: str
    source: str
    price: float | None = None
    currency: str = "EUR"
    image_url: str | None = None
    ean: str | None = None
