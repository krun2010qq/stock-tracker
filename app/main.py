from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.stock_service import get_news, get_quotes

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Stock Tracker", version="1.0.0")

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
    return {"quotes": get_quotes()}


@app.get("/api/news")
def news(limit: int = 24) -> dict:
    return {"news": get_news(limit_per_symbol=max(1, min(limit // 3, 12)))}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
