
from app.setting import settings

import redis


def get_redis():
    """
    建立 Redis 連線
    使用 Pydantic Settings 管理 Redis 配置
    """
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        decode_responses=True  # 讓 Redis 返回字符串而不是 bytes
    )

    try:
        yield r
    finally:
        r.close()
