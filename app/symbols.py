from __future__ import annotations

import re

FEATURED_SYMBOLS: dict[str, str] = {
    "GOOGL": "Alphabet (Google)",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "600519.SS": "贵州茅台",
    "300750.SZ": "宁德时代",
    "000001.SZ": "平安银行",
}

DEFAULT_SYMBOLS: tuple[str, ...] = ("GOOGL", "NVDA", "AVGO")

MIN_FAVORITE_SYMBOLS = 1
MAX_FAVORITE_SYMBOLS = 12
MIN_NEWS_PER_SYMBOL = 2
MAX_NEWS_PER_SYMBOL = 8
DEFAULT_NEWS_PER_SYMBOL = 4

US_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")
ASHARE_SYMBOL_PATTERN = re.compile(r"^\d{6}\.(SS|SZ)$")
ASHARE_CODE_PATTERN = re.compile(r"^\d{6}$")

MARKET_ALL = "all"
MARKET_NASDAQ = "nasdaq"
MARKET_ASHARE = "ashare"
SUPPORTED_MARKETS = (MARKET_ALL, MARKET_NASDAQ, MARKET_ASHARE)


def normalize_ashare_code(code: str) -> str | None:
    if not ASHARE_CODE_PATTERN.fullmatch(code):
        return None
    if code.startswith(("43", "83", "87", "92")):
        return f"{code}.BJ"
    if code.startswith("6"):
        return f"{code}.SS"
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    return None


def canonicalize_symbol(symbol: str) -> str | None:
    raw = symbol.upper().strip()
    if not raw:
        return None

    if ASHARE_SYMBOL_PATTERN.fullmatch(raw):
        return raw

    ashare = normalize_ashare_code(raw)
    if ashare:
        return ashare

    if US_SYMBOL_PATTERN.fullmatch(raw):
        return raw

    return None


def is_ashare_symbol(symbol: str) -> bool:
    return symbol.endswith((".SS", ".SZ"))


def is_us_symbol(symbol: str) -> bool:
    return not is_ashare_symbol(symbol)


def get_market_label(symbol: str) -> str:
    if is_ashare_symbol(symbol):
        return "A股"
    return "纳斯达克/美股"


def normalize_symbols(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for symbol in symbols:
        key = canonicalize_symbol(symbol)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def validate_symbols(symbols: list[str], *, verify_exists: bool = True) -> list[str]:
    normalized = normalize_symbols(symbols)
    if len(normalized) < MIN_FAVORITE_SYMBOLS:
        raise ValueError(f"请至少选择 {MIN_FAVORITE_SYMBOLS} 只股票")
    if len(normalized) > MAX_FAVORITE_SYMBOLS:
        raise ValueError(f"最多选择 {MAX_FAVORITE_SYMBOLS} 只股票")

    if verify_exists:
        from app.symbol_search_service import verify_symbol_exists

        invalid: list[str] = []
        for symbol in normalized:
            if symbol in FEATURED_SYMBOLS:
                continue
            if not verify_symbol_exists(symbol):
                invalid.append(symbol)
        if invalid:
            raise ValueError(f"以下股票代码无效或暂无行情：{', '.join(invalid)}")

    return normalized


def featured_symbols_payload() -> list[dict[str, str]]:
    return [
        {
            "symbol": symbol,
            "name": name,
            "market": get_market_label(symbol),
        }
        for symbol, name in FEATURED_SYMBOLS.items()
    ]
