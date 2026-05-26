from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str


class ProductResultSchema(BaseModel):
    title: str
    price: float | None
    currency: str
    url: str
    source: str
    image_url: str | None
    ean: str | None


class SearchResponse(BaseModel):
    query: str
    query_type: str
    results: list[ProductResultSchema]
