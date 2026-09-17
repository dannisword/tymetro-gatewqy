from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.config import settings
from app.services.user_service import UserService
from app.services.config_service import ConfigService
from app.services.equipment_service import EquipmentService
from app.services.car_service import CarService
from app.services.sensor_service import SensorService
from app.services.setting_log_service import SettingLogService
from app.services.schedule_service import ScheduleService
from app.services.audit_log_service import AuditLogService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/users/login/access-token")

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    return ConfigService(db)

def get_equipment_service(db: Session = Depends(get_db)) -> EquipmentService:
    return EquipmentService(db)

def get_car_service(db: Session = Depends(get_db)) -> CarService:
    return CarService(db)

def get_sensor_service(db: Session = Depends(get_db)) -> SensorService:
    return SensorService(db)

def get_setting_log_service(db: Session = Depends(get_db)) -> SettingLogService:
    return SettingLogService(db)

def get_schedule_service(db: Session = Depends(get_db)) -> ScheduleService:
    return ScheduleService(db)

def get_audit_log_service(db: Session = Depends(get_db)) -> AuditLogService:
    return AuditLogService(db)





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

    user_service = UserService(db)

    # 支援固定 SECRET_KEY 驗證 (Bearer Token 直接帶固定金鑰)
    if token and token == settings.SECRET_KEY:
        admin_user = user_service.get_by_account("admin") or user_service.get_by_id(1)
        if admin_user:
            return admin_user

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
