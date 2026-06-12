from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import User, UserPreference
from app.symbol_catalog import catalog_counts
from app.symbols import (
    DEFAULT_NEWS_PER_SYMBOL,
    DEFAULT_SYMBOLS,
    MAX_NEWS_PER_SYMBOL,
    MIN_NEWS_PER_SYMBOL,
    featured_symbols_payload,
    normalize_symbols,
    validate_symbols,
)


def _default_symbols_json() -> str:
    return json.dumps(list(DEFAULT_SYMBOLS))


def get_or_create_preferences(db: Session, user: User) -> UserPreference:
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if prefs:
        return prefs

    prefs = UserPreference(
        user_id=user.id,
        favorite_symbols=_default_symbols_json(),
        news_per_symbol=DEFAULT_NEWS_PER_SYMBOL,
    )
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return prefs


def get_user_symbols(user: User | None, db: Session | None = None) -> list[str]:
    if user is None:
        return list(DEFAULT_SYMBOLS)

    if db is None:
        return list(DEFAULT_SYMBOLS)

    prefs = get_or_create_preferences(db, user)
    try:
        raw = json.loads(prefs.favorite_symbols or "[]")
    except json.JSONDecodeError:
        raw = []

    symbols = normalize_symbols(raw if isinstance(raw, list) else [])
    return symbols or list(DEFAULT_SYMBOLS)


def get_user_news_limit(user: User | None, db: Session | None = None) -> int:
    if user is None or db is None:
        return DEFAULT_NEWS_PER_SYMBOL

    prefs = get_or_create_preferences(db, user)
    return max(MIN_NEWS_PER_SYMBOL, min(prefs.news_per_symbol, MAX_NEWS_PER_SYMBOL))


def preferences_to_dict(prefs: UserPreference) -> dict:
    try:
        symbols = json.loads(prefs.favorite_symbols or "[]")
    except json.JSONDecodeError:
        symbols = []

    normalized = normalize_symbols(symbols if isinstance(symbols, list) else [])
    return {
        "favorite_symbols": normalized or list(DEFAULT_SYMBOLS),
        "news_per_symbol": max(MIN_NEWS_PER_SYMBOL, min(prefs.news_per_symbol, MAX_NEWS_PER_SYMBOL)),
    }


def update_preferences(db: Session, user: User, favorite_symbols: list[str], news_per_symbol: int) -> UserPreference:
    symbols = validate_symbols(favorite_symbols)
    safe_news_limit = max(MIN_NEWS_PER_SYMBOL, min(news_per_symbol, MAX_NEWS_PER_SYMBOL))

    prefs = get_or_create_preferences(db, user)
    prefs.favorite_symbols = json.dumps(symbols)
    prefs.news_per_symbol = safe_news_limit
    db.commit()
    db.refresh(prefs)
    return prefs


def available_symbols_payload() -> dict:
    counts = catalog_counts()
    return {
        "featured": featured_symbols_payload(),
        "markets": [
            {"key": "all", "label": "全部"},
            {"key": "nasdaq", "label": "纳斯达克"},
            {"key": "ashare", "label": "A股"},
        ],
        "catalog_counts": counts,
        "search_hint": (
            "输入股票代码或公司名称搜索，"
            f"已收录纳斯达克 {counts['nasdaq']} 只、A股 {counts['ashare']} 只"
        ),
        "max_favorites": 12,
    }
