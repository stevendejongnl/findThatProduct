from src.domain.product import ProductResult


class AggregatorService:
    @staticmethod
    def aggregate(results: list[ProductResult]) -> list[ProductResult]:
        seen: set[str] = set()
        unique: list[ProductResult] = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)
        return sorted(unique, key=lambda r: (r.price is None, r.price or 0))
