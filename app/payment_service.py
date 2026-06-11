from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth_service import activate_premium
from app.config import settings
from app.models import PaymentOrder, PaymentProvider, PaymentStatus, User


def generate_order_no() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"ST{timestamp}{secrets.token_hex(4).upper()}"


def wechat_pay_enabled() -> bool:
    return bool(settings.wechat_mch_id and settings.wechat_pay_api_key) and not settings.payment_demo_mode


def alipay_pay_enabled() -> bool:
    return bool(settings.alipay_app_id and settings.alipay_private_key) and not settings.payment_demo_mode


def create_payment_order(db: Session, user: User, provider: PaymentProvider) -> PaymentOrder:
    order = PaymentOrder(
        user_id=user.id,
        order_no=generate_order_no(),
        provider=provider.value,
        amount_yuan=settings.subscription_price_yuan,
        product_code="premium_monthly",
        status=PaymentStatus.PENDING.value,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def build_payment_response(order: PaymentOrder) -> dict:
    if settings.payment_demo_mode:
        demo_url = f"{settings.app_url}/pricing.html?order_no={order.order_no}&provider={order.provider}&demo=1"
        order.pay_url = demo_url
        return {
            "order_no": order.order_no,
            "provider": order.provider,
            "amount_yuan": float(order.amount_yuan),
            "pay_url": demo_url,
            "demo_mode": True,
            "message": "当前为演示模式。接入正式商户号后，将返回真实微信/支付宝支付链接。",
        }

    if order.provider == PaymentProvider.WECHAT.value:
        pay_url = f"{settings.app_url}/api/payments/wechat/pay/{order.order_no}"
    else:
        pay_url = f"{settings.app_url}/api/payments/alipay/pay/{order.order_no}"

    order.pay_url = pay_url
    return {
        "order_no": order.order_no,
        "provider": order.provider,
        "amount_yuan": float(order.amount_yuan),
        "pay_url": pay_url,
        "demo_mode": False,
    }


def mark_order_paid(db: Session, order: PaymentOrder, provider_trade_no: str | None = None) -> User:
    if order.status == PaymentStatus.PAID.value:
        return order.user

    order.status = PaymentStatus.PAID.value
    order.provider_trade_no = provider_trade_no
    order.paid_at = datetime.now(timezone.utc)
    activate_premium(order.user)
    db.commit()
    db.refresh(order.user)
    return order.user


def get_order_by_no(db: Session, order_no: str) -> PaymentOrder | None:
    return db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
