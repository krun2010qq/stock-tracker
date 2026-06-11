from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
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
from app.oauth_service import (
    alipay_oauth_enabled,
    build_alipay_login_url,
    build_wechat_login_url,
    exchange_alipay_code,
    exchange_wechat_code,
    get_or_create_oauth_user,
    new_oauth_state,
    wechat_oauth_enabled,
)
from app.models import OAuthProvider

router = APIRouter(prefix="/api/auth", tags=["auth"])

_oauth_states: dict[str, str] = {}


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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

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


@router.get("/providers")
def providers() -> dict:
    return {
        "wechat": wechat_oauth_enabled(),
        "alipay": alipay_oauth_enabled(),
    }


@router.get("/wechat/login")
def wechat_login() -> RedirectResponse:
    if not wechat_oauth_enabled():
        raise HTTPException(status_code=503, detail="微信登录尚未配置，请在 .env 中填写 WECHAT_APP_ID 和 WECHAT_APP_SECRET")
    state = new_oauth_state()
    _oauth_states[state] = "wechat"
    return RedirectResponse(build_wechat_login_url(state))


@router.get("/wechat/callback")
async def wechat_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    if _oauth_states.pop(state, None) != "wechat":
        raise HTTPException(status_code=400, detail="无效的 OAuth 状态")

    profile = await exchange_wechat_code(code)
    user = get_or_create_oauth_user(
        db,
        OAuthProvider.WECHAT,
        profile["provider_user_id"],
        profile.get("nickname"),
    )
    token = create_access_token(user.id)
    return RedirectResponse(f"/login.html?token={token}")


@router.get("/alipay/login")
def alipay_login() -> RedirectResponse:
    if not alipay_oauth_enabled():
        raise HTTPException(status_code=503, detail="支付宝登录尚未配置，请在 .env 中填写 ALIPAY_APP_ID")
    state = new_oauth_state()
    _oauth_states[state] = "alipay"
    return RedirectResponse(build_alipay_login_url(state))


@router.get("/alipay/callback")
async def alipay_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    if _oauth_states.pop(state, None) != "alipay":
        raise HTTPException(status_code=400, detail="无效的 OAuth 状态")

    profile = await exchange_alipay_code(code)
    user = get_or_create_oauth_user(
        db,
        OAuthProvider.ALIPAY,
        profile["provider_user_id"],
        profile.get("nickname"),
    )
    token = create_access_token(user.id)
    return RedirectResponse(f"/login.html?token={token}")
