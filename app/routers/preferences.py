from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.preferences_service import (
    available_symbols_payload,
    get_or_create_preferences,
    preferences_to_dict,
    update_preferences,
)
from app.symbols import MAX_FAVORITE_SYMBOLS, MAX_NEWS_PER_SYMBOL, MIN_FAVORITE_SYMBOLS, MIN_NEWS_PER_SYMBOL

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class UpdatePreferencesRequest(BaseModel):
    favorite_symbols: list[str] = Field(min_length=MIN_FAVORITE_SYMBOLS, max_length=MAX_FAVORITE_SYMBOLS)
    news_per_symbol: int = Field(ge=MIN_NEWS_PER_SYMBOL, le=MAX_NEWS_PER_SYMBOL)


@router.get("")
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    prefs = get_or_create_preferences(db, user)
    return {
        "preferences": preferences_to_dict(prefs),
        "available_symbols": available_symbols_payload(),
    }


@router.put("")
def save_preferences(
    payload: UpdatePreferencesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        prefs = update_preferences(db, user, payload.favorite_symbols, payload.news_per_symbol)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"preferences": preferences_to_dict(prefs)}
