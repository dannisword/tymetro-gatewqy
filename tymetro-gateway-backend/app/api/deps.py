from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.config import settings
from app.services.user_service import UserService
from app.services.config_service import ConfigService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/users/login/access-token")

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    return ConfigService(db)

# JWT 認證依賴項
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id: str = str(sub)
    except JWTError:
        raise credentials_exception
    
    user_service = UserService(db)
    user = user_service.get_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    return user
