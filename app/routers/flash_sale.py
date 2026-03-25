"""
Flash Sale Router - 核心搶購邏輯
這是整個專案最重要的部分！
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import redis
import pika
import json

from app.database import get_db
from app.models import User, Product, Order
from app.schemas import FlashSaleBuyRequest, FlashSaleBuyResponse
from app.auth import get_current_user
from app.setting import settings
from app.redis import get_redis

router = APIRouter(prefix="/flash-sale", tags=["Flash Sale"])


# Lua Script 用於原子性庫存扣減
# 這是防止超賣的核心！
LUA_DEDUCT_STOCK = """
local key = KEYS[1]
local deduct = tonumber(ARGV[1])
local stock = tonumber(redis.call('GET', key) or 0)

if stock >= deduct then
    redis.call('DECRBY', key, deduct)
    return stock - deduct
else
    return -1
end
"""


def get_and_detuct_product_from_redis(redis_client: redis.Redis, product_id: int, request, product) -> int:
    """
    從 Redis 獲取商品庫存
    """
    try:

        redis_key = f"stock:product:{product_id}"

        # 確保 Redis 中有庫存資料（如果沒有，從資料庫同步）
        if redis_client.get(redis_key) is None:
            redis_client.set(redis_key, product.stock)

        # Step 3: 使用 Lua Script 原子性扣減庫存
        result = redis_client.eval(
            LUA_DEDUCT_STOCK, 1, redis_key, request.quantity)

        if result == -1:
            # 庫存不足
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="庫存不足，搶購失敗"
            )
    except:
        raise


@router.post("/buy/{product_id}", response_model=FlashSaleBuyResponse)
def buy_product(
    product_id: int,
    request: FlashSaleBuyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    搶購商品（核心 API）

    - **product_id**: 商品 ID
    - **quantity**: 購買數量（1-5）

    流程:
    1. 驗證商品是否存在
    2. 使用 Redis Lua Script 原子性扣減庫存
    3. 如果扣減成功，發送訂單到 RabbitMQ 異步處理
    4. 立即返回「排隊中」狀態

    需要在 Header 中提供 JWT Token:
    Authorization: Bearer <your_token>
    """
    # Step 1: 驗證商品是否存在
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到商品 ID: {product_id}"
        )

    # Step 2: 連接 Redis
    if settings.PURCHASE_MODE == "redis":
        try:
            get_and_detuct_product_from_redis(
                redis_client, product_id, request, product)

        except redis.RedisError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Redis 連線失敗: {str(e)}"
            )
    else:
        # 傳統資料庫扣減庫存（不推薦，可能導致超賣）
        if product.stock < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="not enough stock, purchase failed"
            )
        product.stock -= request.quantity
        db.commit()

    # Step 4: 建立訂單（先在資料庫建立，狀態為 pending）
    total_price = product.price * request.quantity

    new_order = Order(
        user_id=current_user.id,
        product_id=product.id,
        quantity=request.quantity,
        total_price=total_price,
        status="pending"
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Step 5: 發送訂單到 RabbitMQ 異步處理
    try:
        # 連接 RabbitMQ
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials
            )
        )
        channel = connection.channel()

        # 宣告 Queue（如果不存在就建立）
        channel.queue_declare(
            queue=settings.RABBITMQ_QUEUE_FLASH_SALE, durable=True)

        # 訂單訊息
        message = {
            "order_id": new_order.id,
            "user_id": current_user.id,
            "product_id": product.id,
            "quantity": request.quantity,
            "total_price": float(total_price)
        }

        # 發送訊息到 Queue
        channel.basic_publish(
            exchange='',
            routing_key=settings.RABBITMQ_QUEUE_FLASH_SALE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 持久化訊息
            )
        )

        connection.close()

    except pika.exceptions.AMQPError as e:
        # RabbitMQ 發送失敗，將訂單標記為 failed
        new_order.status = "failed"
        db.commit()

        # 回滾 Redis 庫存
        redis_key = f"stock:product:{product_id}"
        redis_client.incrby(redis_key, request.quantity)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"訊息佇列發送失敗: {str(e)}"
        )

    # Step 6: 立即返回「排隊中」狀態
    return FlashSaleBuyResponse(
        success=True,
        message="搶購成功！訂單處理中，請稍後查詢訂單狀態",
        order_id=new_order.id,
        status="pending"
    )
