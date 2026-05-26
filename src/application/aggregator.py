import re
from src.domain.product import ProductResult


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _token_set(text: str) -> set[str]:
    return set(_tokens(text))


def _is_relevant(query: str, title: str) -> bool:
    q_tokens = _tokens(query)
    if not q_tokens:
        return True
    t_tokens = _token_set(title)

    # Require all alphanumeric-only tokens (numbers, model codes) to be present
    # These are the most distinctive: "buds2", "pro", "2", model numbers
    specific = [t for t in q_tokens if re.fullmatch(r"[0-9]+|[a-z]+[0-9]+[a-z0-9]*", t)]
    for token in specific:
        if token not in t_tokens:
            # also accept the number embedded: "buds2" → accept if both "buds" and "2" present
            if re.fullmatch(r"[a-z]+[0-9]+", token):
                alpha = re.match(r"[a-z]+", token).group()
                num = re.search(r"[0-9]+", token).group()
                if not (alpha in t_tokens and num in t_tokens):
                    return False
            else:
                return False

    # Require overall coverage >= 0.6
    q_set = set(q_tokens)
    matched = q_set & t_tokens
    return len(matched) / len(q_set) >= 0.6


class AggregatorService:
    @staticmethod
    def aggregate(results: list[ProductResult], query: str = "") -> list[ProductResult]:
        seen: set[str] = set()
        unique: list[ProductResult] = []
        for r in results:
            if r.url in seen:
                continue
            seen.add(r.url)
            if query and not _is_relevant(query, r.title):
                continue
            unique.append(r)

        return sorted(unique, key=lambda r: (r.price is None, r.price or 0))
