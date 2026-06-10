from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.polymarket_service import get_polymarket_by_symbol, get_polymarket_search_url
from app.reddit_service import MAX_NEWS_ITEMS, get_reddit_news
from app.stock_service import get_quotes

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Stock Tracker", version="1.1.0")

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

    for quote in quote_list:
        symbol = quote["symbol"]
        quote["polymarket"] = polymarket.get(symbol, [])
        quote["polymarket_search_url"] = get_polymarket_search_url(symbol)

    return {"quotes": quote_list}


@app.get("/api/news")
def news(limit: int = MAX_NEWS_ITEMS) -> dict:
    safe_limit = max(1, min(limit, MAX_NEWS_ITEMS))
    return {"news": get_reddit_news(limit=safe_limit)}


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
