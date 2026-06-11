from __future__ import annotations

import secrets
import urllib.parse
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import OAuthAccount, OAuthProvider, User


def wechat_oauth_enabled() -> bool:
    return bool(settings.wechat_app_id and settings.wechat_app_secret)


def alipay_oauth_enabled() -> bool:
    return bool(settings.alipay_app_id)


def build_wechat_login_url(state: str) -> str:
    redirect_uri = urllib.parse.quote(f"{settings.app_url}/api/auth/wechat/callback", safe="")
    return (
        "https://open.weixin.qq.com/connect/qrconnect"
        f"?appid={settings.wechat_app_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=snsapi_login"
        f"&state={state}#wechat_redirect"
    )


def build_alipay_login_url(state: str) -> str:
    redirect_uri = urllib.parse.quote(f"{settings.app_url}/api/auth/alipay/callback", safe="")
    return (
        "https://openauth.alipay.com/oauth2/publicAppAuthorize.htm"
        f"?app_id={settings.alipay_app_id}"
        f"&scope=auth_user"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )


def get_or_create_oauth_user(
    db: Session,
    provider: OAuthProvider,
    provider_user_id: str,
    nickname: str | None = None,
) -> User:
    account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == provider.value,
            OAuthAccount.provider_user_id == provider_user_id,
        )
        .first()
    )
    if account:
        return account.user

    user = User(
        display_name=nickname or f"{provider.value}用户",
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=provider.value,
            provider_user_id=provider_user_id,
            provider_nickname=nickname,
        )
    )
    db.commit()
    db.refresh(user)
    return user


async def exchange_wechat_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        if token_data.get("errcode"):
            raise ValueError(token_data.get("errmsg", "WeChat OAuth failed"))

        user_resp = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={
                "access_token": token_data["access_token"],
                "openid": token_data["openid"],
            },
        )
        user_resp.raise_for_status()
        profile = user_resp.json()
        if profile.get("errcode"):
            raise ValueError(profile.get("errmsg", "WeChat profile failed"))

    return {
        "provider_user_id": profile.get("openid") or token_data["openid"],
        "nickname": profile.get("nickname") or "微信用户",
    }


async def exchange_alipay_code(code: str) -> dict:
    if settings.payment_demo_mode and code.startswith("demo_"):
        return {
            "provider_user_id": code.replace("demo_", ""),
            "nickname": "支付宝演示用户",
        }

    raise ValueError("请配置支付宝 OAuth 密钥，或在演示模式下使用 demo 回调")


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)
