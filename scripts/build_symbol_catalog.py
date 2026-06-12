"""Build local NASDAQ and A-share symbol catalogs for offline search."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "symbol_catalog.json"

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
SINA_URL = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def ashare_symbol_from_sina(item: dict) -> str | None:
    code = (item.get("code") or "").strip()
    prefix = (item.get("symbol") or "").strip().lower()
    if not code or len(code) != 6 or not code.isdigit():
        return None
    if prefix.startswith("sh"):
        return f"{code}.SS"
    if prefix.startswith("sz"):
        return f"{code}.SZ"
    if prefix.startswith("bj"):
        return f"{code}.BJ"
    return None


def fetch_nasdaq_symbols(client: httpx.Client) -> list[dict[str, str]]:
    response = client.get(NASDAQ_URL, timeout=60)
    response.raise_for_status()
    rows: list[dict[str, str]] = []
    for line in response.text.strip().splitlines()[1:]:
        if not line or line.startswith("File"):
            continue
        parts = line.split("|")
        if len(parts) < 8:
            continue
        symbol, name, _category, test_issue, _status, _lot, etf, _next = parts[:8]
        if test_issue != "N" or etf != "N":
            continue
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": name.strip(),
                "exchange": "NASDAQ",
                "market_key": "nasdaq",
            }
        )
    return rows


def fetch_ashare_symbols(client: httpx.Client) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    page = 1
    while page <= 120:
        response = client.get(
            SINA_URL,
            params={
                "page": page,
                "num": 80,
                "sort": "symbol",
                "asc": 1,
                "node": "hs_a",
                "symbol": "",
                "_s_r_a": "page",
            },
            timeout=30,
        )
        response.raise_for_status()
        items = response.json()
        if not items:
            break
        for item in items:
            symbol = ashare_symbol_from_sina(item)
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            rows.append(
                {
                    "symbol": symbol,
                    "name": (item.get("name") or symbol).strip(),
                    "exchange": symbol.split(".")[-1],
                    "market_key": "ashare",
                }
            )
        page += 1
    return rows


def main() -> int:
    with httpx.Client(headers=HEADERS) as client:
        nasdaq = fetch_nasdaq_symbols(client)
        ashare = fetch_ashare_symbols(client)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "nasdaq": nasdaq,
        "ashare": ashare,
        "counts": {"nasdaq": len(nasdaq), "ashare": len(ashare)},
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({payload['counts']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
