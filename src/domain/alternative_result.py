from dataclasses import dataclass, field


@dataclass
class AlternativeResult:
    title: str
    reason: str
    url: str
    price: float | None = None
    currency: str = "EUR"
    source: str = "openai"
