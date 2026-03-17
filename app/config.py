"""
Configuration settings loaded from .env file
使用 Pydantic Settings 管理環境變數
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    應用程式設定類別
    自動從 .env 檔案載入環境變數
    """

    # Database Configuration
    POSTGRES_USER: str = Field(default="flash_user")
    POSTGRES_PASSWORD: str = Field(default="flash_password")
    POSTGRES_DB: str = Field(default="flash_sale_db")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)

    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="redis_password")
    REDIS_DB: int = Field(default=0)

    # RabbitMQ Configuration
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_USER: str = Field(default="rabbit_user")
    RABBITMQ_PASSWORD: str = Field(default="rabbit_password")
    RABBITMQ_QUEUE_FLASH_SALE: str = Field(default="flash_sale_orders")

    # JWT Configuration
    JWT_SECRET_KEY: str = Field(default="your-secret-key-change-this-in-production")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # Application Configuration
    APP_TITLE: str = Field(default="Flash Sale API")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)

    @property
    def database_url(self) -> str:
        """
        建構 PostgreSQL 連線 URL
        格式: postgresql://user:password@host:port/database
        """
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """
        建構 Redis 連線 URL
        格式: redis://:password@host:port/db
        """
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 建立全域設定物件（單例模式）
settings = Settings()
