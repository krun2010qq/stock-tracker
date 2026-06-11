from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.dependencies import get_current_user
from app.models import User
from app.polymarket_service import get_polymarket_by_symbol, get_polymarket_search_url
from app.routers import auth, payments
from app.stock_service import get_quotes
from app.yahoo_news_service import NEWS_PER_SYMBOL, get_yahoo_news_by_symbol

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Stock Tracker", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(payments.router)
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


@app.get("/pricing")
@app.get("/pricing.html")
def pricing_page() -> FileResponse:
    return _static_page("pricing.html")


@app.get("/api/quotes")
def quotes(user: User = Depends(get_current_user)) -> dict:
    quote_list = get_quotes()
    polymarket = get_polymarket_by_symbol()
    news_by_symbol = get_yahoo_news_by_symbol(limit=NEWS_PER_SYMBOL)

    for quote in quote_list:
        symbol = quote["symbol"]
        quote["polymarket"] = polymarket.get(symbol, [])
        quote["polymarket_search_url"] = get_polymarket_search_url(symbol)
        quote["news"] = news_by_symbol.get(symbol, [])

    return {"quotes": quote_list, "user": {"is_premium": user.is_premium}}


@app.get("/api/news")
def news(user: User = Depends(get_current_user), limit: int = NEWS_PER_SYMBOL) -> dict:
    safe_limit = max(1, min(limit, NEWS_PER_SYMBOL))
    return {"news_by_symbol": get_yahoo_news_by_symbol(limit=safe_limit)}


@app.get("/api/polymarket")
def polymarket(user: User = Depends(get_current_user)) -> dict:
    data = get_polymarket_by_symbol()
    return {
        "markets": data,
        "search_urls": {symbol: get_polymarket_search_url(symbol) for symbol in data},
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
