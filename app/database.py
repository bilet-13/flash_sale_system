"""
Database connection and session management
使用 SQLAlchemy 管理資料庫連線
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 建立資料庫引擎
# echo=True 會在 console 顯示所有 SQL 語句（開發時很有用）
engine = create_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # 連線前先測試是否有效
    pool_size=10,        # 連線池大小
    max_overflow=20      # 超過 pool_size 後最多再建立幾個連線
)

# 建立 Session 工廠
# autocommit=False: 需要手動 commit
# autoflush=False: 需要手動 flush
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立 ORM Base 類別
# 所有 Model 都要繼承這個 Base
Base = declarative_base()


def get_db():
    """
    依賴注入函數 - 提供資料庫 session

    使用方式:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users

    好處:
        - 自動管理連線（使用完自動關閉）
        - 支援交易（transaction）
        - 線程安全
    """
    db = SessionLocal()
    try:
        yield db  # 提供 session 給路由函數
    finally:
        db.close()  # 確保 session 關閉
