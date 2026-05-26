from dataclasses import dataclass
from enum import Enum
import re


class QueryType(Enum):
    EAN = "ean"
    TEXT = "text"


@dataclass(frozen=True)
class SearchQuery:
    raw: str
    type: QueryType

    @classmethod
    def from_raw(cls, raw: str) -> "SearchQuery":
        raw = raw.strip()
        if len(raw) < 2:
            raise ValueError("Query too short")
        if re.fullmatch(r"\d{8}|\d{13}", raw):
            return cls(raw=raw, type=QueryType.EAN)
        return cls(raw=raw, type=QueryType.TEXT)
