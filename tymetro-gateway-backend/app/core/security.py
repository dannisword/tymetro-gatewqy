import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from jose import jwt
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼 (支援 Bcrypt 雜湊與舊有明文密碼相容)"""
    if not hashed_password:
        return False
    
    try:
        # bcrypt 驗證
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72], 
            hashed_password.encode("utf-8")
        )
    except Exception:
        # 當雜湊不符合格式時，進行明文比對 (相容舊資料)
        return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """取得密碼雜湊 (使用 Bcrypt)"""
    # bcrypt 要求輸入必須是 bytes，且長度限制為 72 bytes
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """創建 JWT Access Token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
