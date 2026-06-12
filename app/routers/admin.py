from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin_service import delete_user, get_admin_stats, list_users, update_user, user_to_admin_dict
from app.database import get_db
from app.dependencies import get_admin_user
from app.models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


@router.get("/stats")
def admin_stats(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> dict:
    return {"stats": get_admin_stats(db)}


@router.get("/users")
def admin_users(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    q: str = Query(default=""),
) -> dict:
    return {"users": list_users(db, q)}


@router.patch("/users/{user_id}")
def admin_update_user(
    user_id: str,
    payload: UpdateUserRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    if user_id == admin.id and payload.is_admin is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能取消自己的管理员权限")
    if user_id == admin.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁用自己的账号")

    try:
        user = update_user(
            db,
            user_id,
            display_name=payload.display_name,
            is_active=payload.is_active,
            is_admin=payload.is_admin,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"user": user_to_admin_dict(user)}


@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己的账号")

    try:
        delete_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"ok": True}
