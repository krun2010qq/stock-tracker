from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

TRACKED_SYMBOLS: dict[str, str] = {
    "GOOGL": "Alphabet (Google)",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
}

CACHE_TTL_SECONDS = 120
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
QUOTE_CACHE_FILE = DATA_DIR / "quotes.json"

_quote_cache: dict[str, Any] = {"expires_at": 0.0, "data": []}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json,application/xml,*/*",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_file_cache() -> list[dict[str, Any]]:
    if not QUOTE_CACHE_FILE.exists():
        return []
    try:
        payload = json.loads(QUOTE_CACHE_FILE.read_text(encoding="utf-8"))
        return payload.get("quotes", [])
    except Exception:
        return []


def _save_file_cache(quotes: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QUOTE_CACHE_FILE.write_text(
        json.dumps({"quotes": quotes, "saved_at": datetime.now(timezone.utc).isoformat()}, indent=2),
        encoding="utf-8",
    )


def _fetch_quote_yahoo(symbol: str, name: str, client: httpx.Client) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1m", "range": "1d"}
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
        "source": "yahoo",
    }


def _fetch_quote_finnhub(symbol: str, name: str, client: httpx.Client, token: str) -> dict[str, Any]:
    response = client.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": token},
    )
    response.raise_for_status()
    payload = response.json()

    price = _safe_float(payload.get("c"))
    previous_close = _safe_float(payload.get("pc"))
    change = _safe_float(payload.get("d"))
    change_percent = _safe_float(payload.get("dp"))

    return {
        "symbol": symbol,
        "name": name,
        "price": price,
        "previous_close": previous_close,
        "change": change,
        "change_percent": change_percent,
        "currency": "USD",
        "market_state": "REGULAR",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "finnhub",
    }


def _fetch_all_quotes() -> list[dict[str, Any]]:
    finnhub_token = os.environ.get("FINNHUB_API_KEY", "").strip()
    quotes: list[dict[str, Any]] = []

    with httpx.Client(timeout=20.0, headers=HEADERS) as client:
        for index, (symbol, name) in enumerate(TRACKED_SYMBOLS.items()):
            if index > 0:
                time.sleep(0.5)

            if finnhub_token:
                try:
                    quotes.append(_fetch_quote_finnhub(symbol, name, client, finnhub_token))
                    continue
                except Exception:
                    pass

            quotes.append(_fetch_quote_yahoo(symbol, name, client))

    if not all(quote.get("price") is not None for quote in quotes):
        raise ValueError("Incomplete quote data")

    return quotes


def get_quotes() -> list[dict[str, Any]]:
    now = time.time()
    if _quote_cache["data"] and now < _quote_cache["expires_at"]:
        return _quote_cache["data"]

    quotes: list[dict[str, Any]] = []
    try:
        quotes = _fetch_all_quotes()
        _save_file_cache(quotes)
    except Exception:
        quotes = _load_file_cache()

    if not quotes:
        quotes = [
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
            }
            for symbol, name in TRACKED_SYMBOLS.items()
        ]

    _quote_cache["data"] = quotes
    _quote_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return quotes
