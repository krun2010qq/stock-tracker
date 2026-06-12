from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.dependencies import get_optional_user
from app.models import User
from app.polymarket_service import get_polymarket_by_symbol, get_polymarket_search_url
from app.preferences_service import available_symbols_payload, get_user_news_limit, get_user_symbols
from app.routers import auth, preferences
from app.stock_service import get_quotes
from app.symbols import DEFAULT_SYMBOLS, DEFAULT_NEWS_PER_SYMBOL
from app.yahoo_news_service import get_yahoo_news_by_symbol

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Stock Tracker", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(preferences.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _static_page(name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / name)


@app.get("/")
def index() -> FileResponse:
    return _static_page("index.html")


@app.get("/login")
@app.get("/login.html")
def login_page() -> FileResponse:
    return _static_page("login.html")


@app.get("/register")
@app.get("/register.html")
def register_page() -> FileResponse:
    return _static_page("register.html")


@app.get("/api/symbols")
def symbols() -> dict:
    return {
        "symbols": available_symbols_payload(),
        "defaults": list(DEFAULT_SYMBOLS),
        "default_news_per_symbol": DEFAULT_NEWS_PER_SYMBOL,
    }


@app.get("/api/quotes")
def quotes(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    tracked_symbols = get_user_symbols(user, db)
    news_limit = get_user_news_limit(user, db)

    quote_list = get_quotes(tracked_symbols)
    polymarket = get_polymarket_by_symbol(tracked_symbols)
    news_by_symbol = get_yahoo_news_by_symbol(tracked_symbols, limit=news_limit)

    for quote in quote_list:
        symbol = quote["symbol"]
        quote["polymarket"] = polymarket.get(symbol, [])
        quote["polymarket_search_url"] = get_polymarket_search_url(symbol)
        quote["news"] = news_by_symbol.get(symbol, [])

    return {
        "quotes": quote_list,
        "tracked_symbols": tracked_symbols,
        "news_per_symbol": news_limit,
        "is_authenticated": user is not None,
    }


@app.get("/api/news")
def news(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
    limit: int = DEFAULT_NEWS_PER_SYMBOL,
) -> dict:
    tracked_symbols = get_user_symbols(user, db)
    news_limit = get_user_news_limit(user, db) if user else max(1, min(limit, DEFAULT_NEWS_PER_SYMBOL))
    return {"news_by_symbol": get_yahoo_news_by_symbol(tracked_symbols, limit=news_limit)}


@app.get("/api/polymarket")
def polymarket(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    tracked_symbols = get_user_symbols(user, db)
    data = get_polymarket_by_symbol(tracked_symbols)
    return {
        "markets": data,
        "search_urls": {symbol: get_polymarket_search_url(symbol) for symbol in data},
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
