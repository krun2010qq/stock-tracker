from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.symbols import DEFAULT_SYMBOLS, MAX_NEWS_PER_SYMBOL

CACHE_TTL_SECONDS = 120

_news_cache: dict[str, Any] = {"expires_at": 0.0, "key": "", "data": {}}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
}


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _cache_key(symbols: tuple[str, ...], limit: int) -> str:
    return f"{','.join(symbols)}:{limit}"


def _fetch_symbol_news(symbol: str, client: httpx.Client, limit: int) -> list[dict[str, Any]]:
    response = client.get(
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        params={"s": symbol, "region": "US", "lang": "en-US"},
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)

    items: list[dict[str, Any]] = []
    for item in root.findall("./channel/item")[:limit]:
        title = _clean_text(item.findtext("title") or "Untitled")
        summary = _clean_text(item.findtext("description") or "")
        if len(summary) > 180:
            summary = summary[:177] + "..."

        items.append(
            {
                "symbol": symbol,
                "title": title,
                "summary": summary or "Yahoo Finance 新闻",
                "url": (item.findtext("link") or "").strip(),
                "publisher": _clean_text(item.findtext("source") or "Yahoo Finance"),
                "published_at": (item.findtext("pubDate") or "").strip(),
            }
        )

    return items


def get_yahoo_news_by_symbol(
    symbols: list[str] | None = None,
    limit: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    requested = tuple(symbols or DEFAULT_SYMBOLS)
    safe_limit = max(1, min(limit, MAX_NEWS_PER_SYMBOL))
    key = _cache_key(requested, safe_limit)
    now = time.time()

    if _news_cache["data"] and _news_cache["key"] == key and now < _news_cache["expires_at"]:
        return {symbol: items[:safe_limit] for symbol, items in _news_cache["data"].items()}

    result: dict[str, list[dict[str, Any]]] = {}

    with httpx.Client(timeout=20.0, headers=HEADERS) as client:
        for index, symbol in enumerate(requested):
            if index > 0:
                time.sleep(0.3)
            try:
                result[symbol] = _fetch_symbol_news(symbol, client, limit=safe_limit)
            except Exception:
                result[symbol] = []

    for symbol in requested:
        result.setdefault(symbol, [])

    _news_cache["data"] = result
    _news_cache["key"] = key
    _news_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return result
