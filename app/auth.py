"""
JWT Authentication utilities
JWT Token 的生成和驗證邏輯
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.setting import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

# 密碼加密上下文（使用 bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密碼流程（告訴 FastAPI 從哪個 endpoint 取得 token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼是否正確

    Args:
        plain_password: 明文密碼（用戶輸入的）
        hashed_password: 加密密碼（資料庫儲存的）

    Returns:
        bool: 密碼是否正確
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    加密密碼

    Args:
        password: 明文密碼

    Returns:
        str: bcrypt 加密後的密碼
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 JWT Access Token

    Args:
        data: 要編碼進 token 的資料（通常是 {"sub": username}）
        expires_delta: Token 過期時間（預設 60 分鐘）

    Returns:
        str: JWT Token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception: HTTPException) -> TokenData:
    """
    驗證 JWT Token

    Args:
        token: JWT Token 字串
        credentials_exception: 驗證失敗時拋出的例外

    Returns:
        TokenData: 解析後的 Token 資料

    Raises:
        HTTPException: Token 無效或過期
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY,
                             algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)
        return token_data

    except JWTError:
        raise credentials_exception


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    取得當前登入的用戶（依賴注入函數）

    使用方式:
        @app.get("/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user

    Args:
        token: JWT Token（自動從 Authorization header 取得）
        db: 資料庫 session

    Returns:
        User: 當前登入的用戶物件

    Raises:
        HTTPException: Token 無效或用戶不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(token, credentials_exception)

    user = db.query(User).filter(User.username == token_data.username).first()

    if user is None:
        raise credentials_exception

    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    驗證用戶身份（用於登入）

    Args:
        db: 資料庫 session
        username: 用戶名
        password: 明文密碼

    Returns:
        User: 驗證成功則返回用戶物件，否則返回 None
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
