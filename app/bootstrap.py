from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.auth_service import get_user_by_email, hash_password
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []
    if "is_admin" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE")
    if "is_premium" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT FALSE")
    if "premium_until" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN premium_until TIMESTAMPTZ")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def ensure_admin_user() -> None:
    email = settings.admin_email.strip().lower()
    password = settings.admin_password.strip()
    if not email or not password:
        return

    db: Session = SessionLocal()
    try:
        user = get_user_by_email(db, email)
        if user:
            changed = False
            if not user.is_admin:
                user.is_admin = True
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                db.commit()
            return

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=settings.admin_display_name,
            is_active=True,
            is_admin=True,
            is_premium=False,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def bootstrap_app() -> None:
    ensure_schema()
    ensure_admin_user()
