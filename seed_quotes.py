import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "data" / "quotes.json"

TRACKED = {
    "GOOGL": "Alphabet (Google)",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
}


def main() -> None:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    quotes = []

    with httpx.Client(timeout=20.0, headers=headers) as client:
        for symbol, name in TRACKED.items():
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            response = client.get(url, params={"interval": "1m", "range": "1d"})
            response.raise_for_status()
            meta = response.json()["chart"]["result"][0]["meta"]
            price = float(meta.get("regularMarketPrice") or meta.get("previousClose"))
            previous_close = float(meta.get("chartPreviousClose") or meta.get("previousClose"))
            change = round(price - previous_close, 2)
            change_percent = round((change / previous_close) * 100, 2)
            quotes.append(
                {
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
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"quotes": quotes}, indent=2), encoding="utf-8")
    print("Wrote", OUTPUT)


if __name__ == "__main__":
    main()
