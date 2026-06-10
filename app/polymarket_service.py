from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

TRACKED_SYMBOLS = ("GOOGL", "NVDA", "AVGO")

POLYMARKET_SEARCH = {
    "GOOGL": "GOOGL Google",
    "NVDA": "NVDA NVIDIA",
    "AVGO": "AVGO Broadcom",
}

CACHE_TTL_SECONDS = 180
_polymarket_cache: dict[str, Any] = {"expires_at": 0.0, "data": {}}

HEADERS = {
    "User-Agent": "stock-tracker/1.0",
    "Accept": "application/json",
}


def _parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _to_percent(value: Any) -> float | None:
    try:
        return round(float(value) * 100, 1)
    except (TypeError, ValueError):
        return None


def _market_url(event_slug: str | None, market_slug: str | None) -> str:
    if event_slug and market_slug and event_slug != market_slug:
        return f"https://polymarket.com/event/{event_slug}/{market_slug}"
    if market_slug:
        return f"https://polymarket.com/event/{market_slug}"
    if event_slug:
        return f"https://polymarket.com/event/{event_slug}"
    return "https://polymarket.com/"


def _fetch_symbol_markets(symbol: str, client: httpx.Client) -> list[dict[str, Any]]:
    query = POLYMARKET_SEARCH.get(symbol, symbol)
    response = client.get(
        "https://gamma-api.polymarket.com/public-search",
        params={
            "q": query,
            "limit_per_type": 5,
            "search_profiles": False,
            "search_tags": False,
            "keep_closed_markets": 0,
        },
    )
    response.raise_for_status()
    payload = response.json()

    markets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for event in payload.get("events") or []:
        if event.get("closed"):
            continue

        event_slug = event.get("slug") or ""
        event_title = event.get("title") or ""

        for market in event.get("markets") or []:
            if market.get("closed"):
                continue

            question = market.get("question") or event_title or "Polymarket market"
            market_slug = market.get("slug") or ""
            dedupe_key = market_slug or question
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            outcomes = _parse_json_list(market.get("outcomes"))
            prices = _parse_json_list(market.get("outcomePrices"))
            yes_odds = _to_percent(prices[0]) if prices else None
            no_odds = _to_percent(prices[1]) if len(prices) > 1 else None

            markets.append(
                {
                    "symbol": symbol,
                    "title": question,
                    "event_title": event_title,
                    "yes_label": outcomes[0] if outcomes else "Yes",
                    "no_label": outcomes[1] if len(outcomes) > 1 else "No",
                    "yes_odds": yes_odds,
                    "no_odds": no_odds,
                    "url": _market_url(event_slug, market_slug),
                    "volume": _safe_float(market.get("volume") or event.get("volume")),
                }
            )

            if len(markets) >= 3:
                return markets

    return markets


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def get_polymarket_by_symbol() -> dict[str, list[dict[str, Any]]]:
    now = time.time()
    if _polymarket_cache["data"] and now < _polymarket_cache["expires_at"]:
        return _polymarket_cache["data"]

    result: dict[str, list[dict[str, Any]]] = {}
    with httpx.Client(timeout=20.0, headers=HEADERS) as client:
        for index, symbol in enumerate(TRACKED_SYMBOLS):
            if index > 0:
                time.sleep(0.4)
            try:
                result[symbol] = _fetch_symbol_markets(symbol, client)
            except Exception:
                result[symbol] = []

    for symbol in TRACKED_SYMBOLS:
        result.setdefault(symbol, [])

    _polymarket_cache["data"] = result
    _polymarket_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return result


def get_polymarket_search_url(symbol: str) -> str:
    return f"https://polymarket.com/search?q={symbol}"
