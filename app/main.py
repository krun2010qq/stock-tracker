from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.polymarket_service import get_polymarket_by_symbol, get_polymarket_search_url
from app.stock_service import get_quotes
from app.yahoo_news_service import NEWS_PER_SYMBOL, get_yahoo_news_by_symbol

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Stock Tracker", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/quotes")
def quotes() -> dict:
    quote_list = get_quotes()
    polymarket = get_polymarket_by_symbol()
    news_by_symbol = get_yahoo_news_by_symbol(limit=NEWS_PER_SYMBOL)

    for quote in quote_list:
        symbol = quote["symbol"]
        quote["polymarket"] = polymarket.get(symbol, [])
        quote["polymarket_search_url"] = get_polymarket_search_url(symbol)
        quote["news"] = news_by_symbol.get(symbol, [])

    return {"quotes": quote_list}


@app.get("/api/news")
def news(limit: int = NEWS_PER_SYMBOL) -> dict:
    safe_limit = max(1, min(limit, NEWS_PER_SYMBOL))
    return {"news_by_symbol": get_yahoo_news_by_symbol(limit=safe_limit)}


@app.get("/api/polymarket")
def polymarket() -> dict:
    data = get_polymarket_by_symbol()
    return {
        "markets": data,
        "search_urls": {symbol: get_polymarket_search_url(symbol) for symbol in data},
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
