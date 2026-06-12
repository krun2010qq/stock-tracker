from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import User, UserPreference
from app.preferences_service import preferences_to_dict


def get_admin_stats(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    admin_users = db.query(func.count(User.id)).filter(User.is_admin.is_(True)).scalar() or 0
    preference_rows = db.query(func.count(UserPreference.user_id)).scalar() or 0
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": max(total_users - active_users, 0),
        "admin_users": admin_users,
        "users_with_preferences": preference_rows,
    }


def user_to_admin_dict(user: User) -> dict:
    prefs = None
    if user.preferences:
        prefs = preferences_to_dict(user.preferences)
    else:
        try:
            raw = json.loads('["GOOGL","NVDA","AVGO"]')
        except json.JSONDecodeError:
            raw = []
        prefs = {"favorite_symbols": raw, "news_per_symbol": 4}

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "is_premium": user.is_premium,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "preferences": prefs,
    }


def list_users(db: Session, query: str = "") -> list[dict]:
    users_query = db.query(User).order_by(User.created_at.desc())
    if query.strip():
        keyword = f"%{query.strip().lower()}%"
        users_query = users_query.filter(
            (func.lower(User.email).like(keyword)) | (func.lower(User.display_name).like(keyword))
        )
    users = users_query.options(joinedload(User.preferences)).all()
    return [user_to_admin_dict(user) for user in users]


def update_user(
    db: Session,
    user_id: str,
    *,
    display_name: str | None = None,
    is_active: bool | None = None,
    is_admin: bool | None = None,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise LookupError("用户不存在")

    if display_name is not None:
        user.display_name = display_name.strip()
    if is_active is not None:
        user.is_active = is_active
    if is_admin is not None:
        user.is_admin = is_admin

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise LookupError("用户不存在")
    db.delete(user)
    db.commit()
