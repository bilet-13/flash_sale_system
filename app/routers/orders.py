"""
Orders Router
處理訂單查詢 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Order
from app.schemas import OrderResponse, OrderDetailResponse
from app.auth import get_current_user

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=List[OrderResponse])
def get_my_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查看我的所有訂單（需要登入）

    - **skip**: 跳過前 N 筆資料（分頁用）
    - **limit**: 最多返回幾筆資料（預設 100）

    需要在 Header 中提供 JWT Token:
    Authorization: Bearer <your_token>
    """
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(
        Order.created_at.desc()  # 最新的訂單在最前面
    ).offset(skip).limit(limit).all()

    return orders


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查看單一訂單詳細資訊（需要登入）

    - **order_id**: 訂單 ID

    只能查看自己的訂單，無法查看別人的訂單

    需要在 Header 中提供 JWT Token:
    Authorization: Bearer <your_token>
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到訂單 ID: {order_id}"
        )

    # 檢查訂單是否屬於當前用戶
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權查看此訂單"
        )

    return order


@router.get("/{order_id}/status", response_model=dict)
def get_order_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查看訂單狀態（需要登入）

    - **order_id**: 訂單 ID

    返回訂單的即時狀態:
    - pending: 處理中
    - completed: 已完成
    - failed: 失敗
    - cancelled: 已取消

    需要在 Header 中提供 JWT Token:
    Authorization: Bearer <your_token>
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到訂單 ID: {order_id}"
        )

    # 檢查訂單是否屬於當前用戶
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權查看此訂單"
        )

    return {
        "order_id": order.id,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at
    }
