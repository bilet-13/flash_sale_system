"""
Products Router
處理商品相關 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import redis

from app.database import get_db
from app.models import Product
from app.schemas import ProductResponse, ProductStockResponse
from app.config import settings

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=List[ProductResponse])
def get_products(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    列出所有商品

    - **skip**: 跳過前 N 筆資料（分頁用）
    - **limit**: 最多返回幾筆資料（預設 100）
    """
    products = db.query(Product).offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    取得單一商品詳細資訊

    - **product_id**: 商品 ID
    """
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到商品 ID: {product_id}"
        )

    return product


@router.get("/{product_id}/stock", response_model=ProductStockResponse)
def get_product_stock(product_id: int, db: Session = Depends(get_db)):
    """
    取得商品即時庫存（優先從 Redis 讀取）

    - **product_id**: 商品 ID

    流程:
    1. 先嘗試從 Redis 讀取即時庫存
    2. 如果 Redis 沒有，則從資料庫讀取
    3. 返回庫存數量和資料來源
    """
    # 先從資料庫取得商品資訊（確認商品存在）
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到商品 ID: {product_id}"
        )

    # 嘗試從 Redis 讀取即時庫存
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        redis_key = f"stock:product:{product_id}"
        stock = r.get(redis_key)

        if stock is not None:
            return ProductStockResponse(
                product_id=product.id,
                name=product.name,
                stock=int(stock),
                source="redis"
            )

    except redis.RedisError:
        # Redis 連線失敗，使用資料庫庫存
        pass

    # 如果 Redis 沒有，返回資料庫庫存
    return ProductStockResponse(
        product_id=product.id,
        name=product.name,
        stock=product.stock,
        source="database"
    )
