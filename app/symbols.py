from __future__ import annotations

AVAILABLE_SYMBOLS: dict[str, str] = {
    "GOOGL": "Alphabet (Google)",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    "AMD": "AMD",
    "NFLX": "Netflix",
}

DEFAULT_SYMBOLS: tuple[str, ...] = ("GOOGL", "NVDA", "AVGO")

MIN_FAVORITE_SYMBOLS = 1
MAX_FAVORITE_SYMBOLS = 6
MIN_NEWS_PER_SYMBOL = 2
MAX_NEWS_PER_SYMBOL = 8
DEFAULT_NEWS_PER_SYMBOL = 4

POLYMARKET_SEARCH: dict[str, str] = {
    "GOOGL": "GOOGL Google",
    "NVDA": "NVDA NVIDIA",
    "AVGO": "AVGO Broadcom",
    "AAPL": "AAPL Apple",
    "MSFT": "MSFT Microsoft",
    "AMZN": "AMZN Amazon",
    "META": "META Facebook",
    "TSLA": "TSLA Tesla",
    "AMD": "AMD",
    "NFLX": "NFLX Netflix",
}


def normalize_symbols(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for symbol in symbols:
        key = symbol.upper().strip()
        if not key or key not in AVAILABLE_SYMBOLS or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def validate_symbols(symbols: list[str]) -> list[str]:
    normalized = normalize_symbols(symbols)
    if len(normalized) < MIN_FAVORITE_SYMBOLS:
        raise ValueError(f"请至少选择 {MIN_FAVORITE_SYMBOLS} 只股票")
    if len(normalized) > MAX_FAVORITE_SYMBOLS:
        raise ValueError(f"最多选择 {MAX_FAVORITE_SYMBOLS} 只股票")
    return normalized
