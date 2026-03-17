"""
Pydantic Schemas for API request/response validation
定義 API 的請求和回應格式
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ==================== User Schemas ====================

class UserRegister(BaseModel):
    """註冊請求 Schema"""
    username: str = Field(..., min_length=3, max_length=50, description="用戶名（3-50字元）")
    email: EmailStr = Field(..., description="Email 地址")
    password: str = Field(..., min_length=6, description="密碼（至少6字元）")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "william",
                "email": "william@example.com",
                "password": "password123"
            }
        }
    )


class UserLogin(BaseModel):
    """登入請求 Schema"""
    username: str = Field(..., description="用戶名")
    password: str = Field(..., description="密碼")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "william",
                "password": "password123"
            }
        }
    )


class UserResponse(BaseModel):
    """用戶回應 Schema"""
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT Token 回應 Schema"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT Token 內容 Schema"""
    username: Optional[str] = None


# ==================== Product Schemas ====================

class ProductResponse(BaseModel):
    """商品回應 Schema"""
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    stock: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductStockResponse(BaseModel):
    """商品庫存回應 Schema（從 Redis 讀取）"""
    product_id: int
    name: str
    stock: int
    source: str = "redis"  # 'redis' or 'database'


# ==================== Order Schemas ====================

class OrderCreate(BaseModel):
    """建立訂單請求 Schema（內部使用）"""
    user_id: int
    product_id: int
    quantity: int = 1
    total_price: Decimal


class OrderResponse(BaseModel):
    """訂單回應 Schema"""
    id: int
    user_id: int
    product_id: int
    quantity: int
    total_price: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(BaseModel):
    """訂單詳細資訊回應 Schema（包含用戶和商品資訊）"""
    id: int
    user: UserResponse
    product: ProductResponse
    quantity: int
    total_price: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Flash Sale Schemas ====================

class FlashSaleBuyRequest(BaseModel):
    """搶購請求 Schema"""
    quantity: int = Field(default=1, ge=1, le=5, description="購買數量（1-5）")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity": 1
            }
        }
    )


class FlashSaleBuyResponse(BaseModel):
    """搶購回應 Schema"""
    success: bool
    message: str
    order_id: Optional[int] = None
    status: str  # 'pending', 'completed', 'failed'

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "搶購成功！訂單處理中",
                "order_id": 123,
                "status": "pending"
            }
        }
    )


# ==================== Generic Response Schemas ====================

class MessageResponse(BaseModel):
    """通用訊息回應 Schema"""
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "操作成功"
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """健康檢查回應 Schema"""
    status: str
    database: str
    redis: str
    rabbitmq: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "database": "connected",
                "redis": "connected",
                "rabbitmq": "connected"
            }
        }
    )
