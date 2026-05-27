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


class AlternativeSchema(BaseModel):
    title: str
    reason: str
    price: float | None
    currency: str
    url: str
    source: str


class SearchResponse(BaseModel):
    query: str
    query_type: str
    results: list[ProductResultSchema]
    alternatives: list[AlternativeSchema] = []
    enriched: bool = False
    warnings: list[str] = []


class ExplainRequest(BaseModel):
    title: str
    url: str
    price: float | None
    query: str


class ExplainResponse(BaseModel):
    explanation: str | None
    warnings: list[str] = []
