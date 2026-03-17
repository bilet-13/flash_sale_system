"""
FastAPI Application Entry Point
應用程式主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
import pika
from sqlalchemy import text

from app.config import settings
from app.database import engine, get_db
from app.routers import auth, products, orders, flash_sale

# 建立 FastAPI 應用
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="""
    ## Flash Sale System API

    高併發搶購系統 - 後端 API

    ### 功能特色
    * 🔐 JWT 認證系統
    * 🛍️ 商品管理
    * 🔥 高併發搶購（Redis + Lua Script 防止超賣）
    * 📦 訂單管理
    * 🚀 異步處理（RabbitMQ）

    ### 技術棧
    * FastAPI + PostgreSQL + Redis + RabbitMQ
    * Docker Compose 容器化部署

    ### 如何使用
    1. 先註冊帳號: `POST /auth/register`
    2. 登入取得 Token: `POST /auth/login`
    3. 使用 Token 進行搶購: `POST /flash-sale/buy/{product_id}`
    4. 查詢訂單狀態: `GET /orders`
    """,
    docs_url="/docs",  # Swagger UI 路徑
    redoc_url="/redoc"  # ReDoc 路徑
)

# CORS 設定（允許前端跨域請求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應該限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(flash_sale.router)
app.include_router(orders.router)


@app.get("/", tags=["Root"])
def root():
    """
    根路徑 - API 歡迎訊息
    """
    return {
        "message": "歡迎使用 Flash Sale API",
        "docs": "/docs",
        "version": settings.APP_VERSION
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """
    健康檢查 - 檢查所有服務是否正常

    檢查項目:
    - API 狀態
    - PostgreSQL 資料庫連線
    - Redis 連線
    - RabbitMQ 連線
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "rabbitmq": "unknown"
    }

    # 檢查資料庫連線
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    finally:
        db.close()

    # 檢查 Redis 連線
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB
        )
        r.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # 檢查 RabbitMQ 連線
    try:
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
        connection.close()
        health_status["rabbitmq"] = "connected"
    except Exception as e:
        health_status["rabbitmq"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


# 啟動事件
@app.on_event("startup")
def startup_event():
    """
    應用程式啟動時執行
    """
    print("🚀 Flash Sale API 啟動中...")
    print(f"📚 API 文件: http://localhost:8000/docs")
    print(f"🏥 健康檢查: http://localhost:8000/health")


# 關閉事件
@app.on_event("shutdown")
def shutdown_event():
    """
    應用程式關閉時執行
    """
    print("👋 Flash Sale API 關閉")
