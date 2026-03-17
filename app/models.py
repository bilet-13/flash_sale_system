"""
SQLAlchemy ORM Models
對應資料庫的 tables（users, products, orders）
"""
from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    用戶資料表 ORM Model
    對應 SQL: CREATE TABLE users (...)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 關聯：一個用戶可以有多個訂單
    orders = relationship("Order", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Product(Base):
    """
    商品資料表 ORM Model
    對應 SQL: CREATE TABLE products (...)
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String)
    price = Column(DECIMAL(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 約束：價格和庫存不能為負
    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_positive'),
        CheckConstraint('stock >= 0', name='check_stock_positive'),
    )

    # 關聯：一個商品可以在多個訂單中
    orders = relationship("Order", back_populates="product")

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', stock={self.stock})>"


class Order(Base):
    """
    訂單資料表 ORM Model
    對應 SQL: CREATE TABLE orders (...)
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 約束
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('total_price >= 0', name='check_total_price_positive'),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'cancelled')",
            name='check_status_valid'
        ),
    )

    # 關聯：訂單屬於一個用戶、包含一個商品
    user = relationship("User", back_populates="orders")
    product = relationship("Product", back_populates="orders")

    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, status='{self.status}')>"
