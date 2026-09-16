import os
from typing import Optional
from pydantic_settings import BaseSettings
from app.core.logger import logger

class Settings(BaseSettings):

    """
    全域環境變數與安全設定 (.env)
    備註：PLC 點位、Modbus 設定、中央 Server 連線資訊與 Gateway ID 
    已依 SDS 規格書統一收攬至 gateway.yaml 中。
    """
    APP_MODE: str = os.getenv("APP_MODE", "development")
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", 5400))
    
    # 資料庫與 PLC 網段設定
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "gateway.db")
    PLC_IP_SUBNET: Optional[str] = os.getenv("PLC_IP_SUBNET", None)  # 如: "192.168.68" (測試區) 或 "192.168.16" (正式區)

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"sqlite:///./{self.SQLITE_DB_PATH}"


    # Logging
    LOG_PATH: str = os.getenv("LOG_PATH", "app/logs/gateway.log")

    # JWT 認證密鑰
    SECRET_KEY: str = os.getenv("SECRET_KEY", "2sXk8QvJ4mYwN7eLcP5gZh9RuTf3BaD1KiVx6EnWq0MoHy8CrSjL4UpGbNz7FdAeI")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # 外部中央後端連線設定 (支援帳密或固定 SECRET_KEY 兩種驗證方式)
    TYMETRO_BACKEND_URL: str = os.getenv("TYMETRO_BACKEND_URL", "http://220.133.144.73:8901")
    TYMETRO_BACKEND_AUTH_TYPE: str = os.getenv("TYMETRO_BACKEND_AUTH_TYPE", "secret_key")  # "secret_key" 或 "password"
    TYMETRO_BACKEND_SECRET_KEY: str = os.getenv("TYMETRO_BACKEND_SECRET_KEY", "")
    TYMETRO_BACKEND_USERNAME: str = os.getenv("TYMETRO_BACKEND_USERNAME", "admin")
    TYMETRO_BACKEND_PASSWORD: str = os.getenv("TYMETRO_BACKEND_PASSWORD", "admin123")

settings = Settings()

logger.info(f"App Mode: {settings.APP_MODE}")
logger.info(f"Database URL: {settings.SQLALCHEMY_DATABASE_URL}")
