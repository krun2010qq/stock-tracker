from __future__ import annotations

import time
from typing import Any

import httpx

from app.symbols import (
    MARKET_ALL,
    MARKET_ASHARE,
    MARKET_NASDAQ,
    canonicalize_symbol,
    get_market_label,
    is_ashare_symbol,
)

SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
CACHE_TTL_SECONDS = 300
MAX_RESULTS = 20

NASDAQ_EXCHANGES = {"NMS", "NGM", "NCM", "NAS", "NASDAQ"}
ASHARE_EXCHANGES = {"SHH", "SHZ", "SHE", "SSE", "SZSE"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

_search_cache: dict[str, Any] = {"expires_at": 0.0, "key": "", "data": []}


def _cache_key(query: str, market: str) -> str:
    return f"{market}:{query.lower().strip()}"


def _quote_market(item: dict[str, Any]) -> str:
    symbol = (item.get("symbol") or "").upper()
    exchange = (item.get("exchange") or "").upper()
    if symbol.endswith((".SS", ".SZ")) or exchange in ASHARE_EXCHANGES:
        return MARKET_ASHARE
    if exchange in NASDAQ_EXCHANGES:
        return MARKET_NASDAQ
    return MARKET_ALL


def _matches_market(item: dict[str, Any], market: str) -> bool:
    if market == MARKET_ALL:
        symbol = (item.get("symbol") or "").upper()
        exchange = (item.get("exchange") or "").upper()
        quote_type = (item.get("quoteType") or "").upper()
        if quote_type and quote_type not in {"EQUITY", "ETF"}:
            return False
        if symbol.endswith((".SS", ".SZ")) or exchange in ASHARE_EXCHANGES:
            return True
        if exchange in NASDAQ_EXCHANGES:
            return True
        return False

    item_market = _quote_market(item)
    if market == MARKET_NASDAQ:
        return item_market == MARKET_NASDAQ
    if market == MARKET_ASHARE:
        return item_market == MARKET_ASHARE
    return True


def _format_result(item: dict[str, Any]) -> dict[str, str]:
    symbol = (item.get("symbol") or "").upper()
    name = item.get("shortname") or item.get("longname") or symbol
    exchange = item.get("exchange") or ""
    return {
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
        "market": get_market_label(symbol),
        "market_key": _quote_market(item),
    }


def search_symbols(query: str, market: str = MARKET_ALL, limit: int = MAX_RESULTS) -> list[dict[str, str]]:
    query = query.strip()
    if len(query) < 1:
        return []

    market = market if market in {MARKET_ALL, MARKET_NASDAQ, MARKET_ASHARE} else MARKET_ALL
    limit = max(1, min(limit, MAX_RESULTS))
    key = _cache_key(query, market)
    now = time.time()

    if _search_cache["data"] and _search_cache["key"] == key and now < _search_cache["expires_at"]:
        return _search_cache["data"][:limit]

    canonical = canonicalize_symbol(query)
    search_query = canonical or query

    try:
        with httpx.Client(timeout=15.0, headers=HEADERS) as client:
            response = client.get(
                SEARCH_URL,
                params={"q": search_query, "quotesCount": 40, "newsCount": 0},
            )
            if response.status_code == 429:
                return []
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in payload.get("quotes") or []:
        if not _matches_market(item, market):
            continue

        formatted = _format_result(item)
        symbol = formatted["symbol"]
        if not symbol or symbol in seen:
            continue

        seen.add(symbol)
        results.append(formatted)
        if len(results) >= limit:
            break

    _search_cache["data"] = results
    _search_cache["key"] = key
    _search_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return results[:limit]


def verify_symbol_exists(symbol: str) -> bool:
    symbol = (symbol or "").upper().strip()
    if not symbol:
        return False

    results = search_symbols(symbol, market=MARKET_ALL, limit=10)
    if any(item["symbol"] == symbol for item in results):
        return True

    chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        with httpx.Client(timeout=12.0, headers=HEADERS) as client:
            response = client.get(chart_url, params={"interval": "1d", "range": "1d"})
            if response.status_code == 429:
                return canonicalize_symbol(symbol) is not None
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return False

    chart_result = (payload.get("chart") or {}).get("result") or []
    if not chart_result:
        return False

    meta = chart_result[0].get("meta") or {}
    chart_symbol = (meta.get("symbol") or "").upper()
    price = meta.get("regularMarketPrice") or meta.get("previousClose")
    return chart_symbol == symbol and price is not None
