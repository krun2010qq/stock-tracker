from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.symbols import (
    MARKET_ALL,
    MARKET_ASHARE,
    MARKET_NASDAQ,
    canonicalize_symbol,
    get_market_label,
    normalize_ashare_code,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "symbol_catalog.json"


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, list[dict[str, str]]]:
    if not CATALOG_PATH.exists():
        return {"nasdaq": [], "ashare": []}
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {
        "nasdaq": payload.get("nasdaq") or [],
        "ashare": payload.get("ashare") or [],
    }


@lru_cache(maxsize=1)
def _symbol_index() -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    catalog = _load_catalog()
    for market_key in ("nasdaq", "ashare"):
        for item in catalog.get(market_key) or []:
            symbol = (item.get("symbol") or "").upper()
            if symbol and symbol not in index:
                index[symbol] = item
    return index


def catalog_counts() -> dict[str, int]:
    catalog = _load_catalog()
    return {
        "nasdaq": len(catalog.get("nasdaq") or []),
        "ashare": len(catalog.get("ashare") or []),
    }


def catalog_has_symbol(symbol: str) -> bool:
    symbol = (symbol or "").upper().strip()
    if not symbol:
        return False
    return symbol in _symbol_index()


def _iter_candidates(market: str) -> list[dict[str, str]]:
    catalog = _load_catalog()
    if market == MARKET_NASDAQ:
        return list(catalog.get("nasdaq") or [])
    if market == MARKET_ASHARE:
        return list(catalog.get("ashare") or [])
    return list(catalog.get("nasdaq") or []) + list(catalog.get("ashare") or [])


def _score_match(query: str, item: dict[str, str]) -> int:
    symbol = (item.get("symbol") or "").upper()
    name = (item.get("name") or "").upper()
    code = symbol.split(".")[0]
    if symbol == query or code == query:
        return 100
    if symbol.startswith(query) or code.startswith(query):
        return 80
    if query in symbol or query in name:
        return 60
    if query in code:
        return 50
    return 0


def search_local_symbols(query: str, market: str = MARKET_ALL, limit: int = 20) -> list[dict[str, str]]:
    query = query.strip()
    if not query:
        return []

    canonical = canonicalize_symbol(query)
    search_terms = {query.lower()}
    if canonical:
        search_terms.add(canonical.lower())
        search_terms.add(canonical.split(".")[0].lower())

    ranked: list[tuple[int, dict[str, str]]] = []
    for item in _iter_candidates(market):
        symbol = (item.get("symbol") or "").upper()
        name = item.get("name") or symbol
        best = 0
        for term in search_terms:
            best = max(best, _score_match(term.upper(), item))
        if best <= 0:
            continue
        ranked.append(
            (
                best,
                {
                    "symbol": symbol,
                    "name": name,
                    "exchange": item.get("exchange") or "",
                    "market": get_market_label(symbol),
                    "market_key": item.get("market_key") or MARKET_ALL,
                },
            )
        )

    ranked.sort(key=lambda pair: (-pair[0], pair[1]["symbol"]))
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for _score, item in ranked:
        if item["symbol"] in seen:
            continue
        seen.add(item["symbol"])
        results.append(item)
        if len(results) >= limit:
            break
    return results


def lookup_local_symbol(symbol: str) -> dict[str, str] | None:
    symbol = (symbol or "").upper().strip()
    if not symbol:
        return None
    item = _symbol_index().get(symbol)
    if not item:
        return None
    return {
        "symbol": symbol,
        "name": item.get("name") or symbol,
        "exchange": item.get("exchange") or "",
        "market": get_market_label(symbol),
        "market_key": item.get("market_key") or MARKET_ALL,
    }
