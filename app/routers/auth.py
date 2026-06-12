from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth_service import (
    create_access_token,
    get_user_by_email,
    hash_password,
    user_to_dict,
    verify_password,
)
from app.database import get_db
from app.dependencies import get_current_user, serialize_user
from app.models import User
from app.preferences_service import get_or_create_preferences

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    display_name: str = Field(default="个人用户", min_length=1, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower().strip()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已注册")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        is_active=True,
        is_premium=False,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    get_or_create_preferences(db, user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=user_to_dict(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=user_to_dict(user))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"user": serialize_user(user)}
