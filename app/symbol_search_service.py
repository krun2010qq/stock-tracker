from __future__ import annotations

import time
from typing import Any

import httpx

from app.symbol_catalog import catalog_has_symbol, search_local_symbols
from app.symbols import (
    MARKET_ALL,
    canonicalize_symbol,
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

_yahoo_cache: dict[str, Any] = {"expires_at": 0.0, "key": "", "data": []}


def _cache_key(query: str, market: str) -> str:
    return f"{market}:{query.lower().strip()}"


def _merge_results(*groups: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            symbol = (item.get("symbol") or "").upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            merged.append(item)
            if len(merged) >= limit:
                return merged
    return merged


def _search_yahoo(query: str, market: str, limit: int) -> list[dict[str, str]]:
    from app.symbols import MARKET_ASHARE, MARKET_NASDAQ, get_market_label

    key = _cache_key(query, market)
    now = time.time()
    if _yahoo_cache["data"] and _yahoo_cache["key"] == key and now < _yahoo_cache["expires_at"]:
        return _yahoo_cache["data"][:limit]

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

    def quote_market(item: dict[str, Any]) -> str:
        symbol = (item.get("symbol") or "").upper()
        exchange = (item.get("exchange") or "").upper()
        if symbol.endswith((".SS", ".SZ", ".BJ")) or exchange in ASHARE_EXCHANGES:
            return MARKET_ASHARE
        if exchange in NASDAQ_EXCHANGES:
            return MARKET_NASDAQ
        return MARKET_ALL

    def matches_market(item: dict[str, Any]) -> bool:
        if market == MARKET_ALL:
            symbol = (item.get("symbol") or "").upper()
            exchange = (item.get("exchange") or "").upper()
            quote_type = (item.get("quoteType") or "").upper()
            if quote_type and quote_type not in {"EQUITY", "ETF"}:
                return False
            if symbol.endswith((".SS", ".SZ", ".BJ")) or exchange in ASHARE_EXCHANGES:
                return True
            if exchange in NASDAQ_EXCHANGES:
                return True
            return False
        return quote_market(item) == market

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in payload.get("quotes") or []:
        if not matches_market(item):
            continue
        symbol = (item.get("symbol") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        results.append(
            {
                "symbol": symbol,
                "name": item.get("shortname") or item.get("longname") or symbol,
                "exchange": item.get("exchange") or "",
                "market": get_market_label(symbol),
                "market_key": quote_market(item),
            }
        )
        if len(results) >= limit:
            break

    _yahoo_cache["data"] = results
    _yahoo_cache["key"] = key
    _yahoo_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return results[:limit]


def search_symbols(query: str, market: str = MARKET_ALL, limit: int = MAX_RESULTS) -> list[dict[str, str]]:
    query = query.strip()
    if len(query) < 1:
        return []

    market = market if market in {MARKET_ALL, "nasdaq", "ashare"} else MARKET_ALL
    limit = max(1, min(limit, MAX_RESULTS))

    local_results = search_local_symbols(query, market=market, limit=limit)
    if len(local_results) >= limit:
        return local_results

    yahoo_results = _search_yahoo(query, market, limit=limit)
    return _merge_results(local_results, yahoo_results, limit=limit)


def verify_symbol_exists(symbol: str) -> bool:
    symbol = (symbol or "").upper().strip()
    if not symbol:
        return False

    if catalog_has_symbol(symbol):
        return True

    chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        with httpx.Client(timeout=12.0, headers=HEADERS) as client:
            response = client.get(chart_url, params={"interval": "1d", "range": "1d"})
            if response.status_code == 429:
                return False
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
