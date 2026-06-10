from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

TRACKED_SYMBOLS: dict[str, str] = {
    "GOOGL": "Alphabet (Google)",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
}

CACHE_TTL_SECONDS = 30
_quote_cache: dict[str, Any] = {"expires_at": 0.0, "data": []}
_news_cache: dict[str, Any] = {"expires_at": 0.0, "data": []}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StockTracker/1.0)",
    "Accept": "application/json,text/xml,*/*",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_quote(symbol: str, name: str) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1m", "range": "1d"}

    with httpx.Client(timeout=20.0, headers=HEADERS) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError(f"No chart data for {symbol}")

    meta = result[0].get("meta") or {}
    price = _safe_float(meta.get("regularMarketPrice") or meta.get("previousClose"))
    previous_close = _safe_float(meta.get("chartPreviousClose") or meta.get("previousClose"))

    change = None
    change_percent = None
    if price is not None and previous_close not in (None, 0):
        change = round(price - previous_close, 2)
        change_percent = round((change / previous_close) * 100, 2)

    return {
        "symbol": symbol,
        "name": name,
        "price": price,
        "previous_close": previous_close,
        "change": change,
        "change_percent": change_percent,
        "currency": meta.get("currency") or "USD",
        "market_state": meta.get("marketState") or "REGULAR",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_symbol_news(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline"
    params = {"s": symbol, "region": "US", "lang": "en-US"}

    with httpx.Client(timeout=20.0, headers=HEADERS) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.text)

    items: list[dict[str, Any]] = []
    for item in root.findall("./channel/item")[:limit]:
        title = (item.findtext("title") or "Untitled").strip()
        link = (item.findtext("link") or "").strip()
        summary = (item.findtext("description") or "").strip()
        published_at = (item.findtext("pubDate") or "").strip()
        publisher = (item.findtext("source") or "Yahoo Finance").strip()

        items.append(
            {
                "symbol": symbol,
                "title": title,
                "summary": summary,
                "url": link,
                "publisher": publisher,
                "published_at": published_at,
                "thumbnail": None,
            }
        )

    return items


def get_quotes() -> list[dict[str, Any]]:
    now = time.time()
    if _quote_cache["data"] and now < _quote_cache["expires_at"]:
        return _quote_cache["data"]

    quotes: list[dict[str, Any]] = []
    for symbol, name in TRACKED_SYMBOLS.items():
        try:
            quotes.append(_fetch_quote(symbol, name))
        except Exception as exc:
            quotes.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "price": None,
                    "previous_close": None,
                    "change": None,
                    "change_percent": None,
                    "currency": "USD",
                    "market_state": "ERROR",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc),
                }
            )

    _quote_cache["data"] = quotes
    _quote_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return quotes


def get_news(limit_per_symbol: int = 8) -> list[dict[str, Any]]:
    now = time.time()
    if _news_cache["data"] and now < _news_cache["expires_at"]:
        return _news_cache["data"]

    all_news: list[dict[str, Any]] = []
    for symbol in TRACKED_SYMBOLS:
        try:
            all_news.extend(_fetch_symbol_news(symbol, limit=limit_per_symbol))
        except Exception:
            continue

    all_news.sort(
        key=lambda item: item.get("published_at") or "",
        reverse=True,
    )

    _news_cache["data"] = all_news
    _news_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return all_news
