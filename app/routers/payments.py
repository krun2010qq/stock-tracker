from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import PaymentProvider, User
from app.payment_service import (
    build_payment_response,
    create_payment_order,
    get_order_by_no,
    mark_order_paid,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CreatePaymentRequest(BaseModel):
    provider: Literal["wechat", "alipay"]


@router.get("/plans")
def plans() -> dict:
    return {
        "plans": [
            {
                "code": "premium_monthly",
                "name": "高级会员（月付）",
                "price_yuan": settings.subscription_price_yuan,
                "days": settings.subscription_days,
                "features": ["完整股价面板", "Polymarket 赔率", "Yahoo 新闻", "会员标识"],
            }
        ],
        "demo_mode": settings.payment_demo_mode,
    }


@router.post("/create")
def create_payment(
    payload: CreatePaymentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    provider = PaymentProvider(payload.provider)
    order = create_payment_order(db, user, provider)
    response = build_payment_response(order)
    db.commit()
    return response


@router.post("/demo/complete/{order_no}")
def demo_complete_payment(
    order_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not settings.payment_demo_mode:
        raise HTTPException(status_code=403, detail="演示支付已关闭")

    order = get_order_by_no(db, order_no)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="订单不存在")

    updated_user = mark_order_paid(db, order, provider_trade_no=f"demo-{order.order_no}")
    return {
        "message": "演示支付成功，会员已开通",
        "user": {
            "id": updated_user.id,
            "is_premium": updated_user.is_premium,
            "premium_until": updated_user.premium_until.isoformat() if updated_user.premium_until else None,
        },
    }


@router.get("/orders/{order_no}")
def get_payment_order(
    order_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    order = get_order_by_no(db, order_no)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "order_no": order.order_no,
        "provider": order.provider,
        "amount_yuan": float(order.amount_yuan),
        "status": order.status,
        "pay_url": order.pay_url,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
    }
