"""
Pytest 設定檔
所有測試共用的 fixtures（測試工具）都放在這裡
"""
import pytest
import redis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.config import settings

# 測試用的 DB URL：跟 production 同一台 PostgreSQL，但用不同的 DB
TEST_DATABASE_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/test_flash_sale"
)

# 建立測試用的 engine 和 SessionLocal
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    所有測試開始前：建立所有 table
    所有測試結束後：刪除所有 table
    """
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def clean_tables():
    """
    每個測試結束後清空所有 table 的資料，並清除 Redis 庫存 keys
    保證每個測試都從乾淨的狀態開始
    """
    yield
    # 清 PostgreSQL
    db = TestSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()

    # 清 Redis 的所有庫存 keys
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB
    )
    for key in r.scan_iter("stock:*"):
        r.delete(key)


@pytest.fixture
def db():
    """
    提供測試用的 DB session
    """
    database = TestSessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def client(db):
    """
    提供測試用的 HTTP client
    自動把 get_db 替換成測試用的 DB session
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
