import os
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
    
    # 資料庫設定
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "gateway.db")

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"sqlite:///./{self.SQLITE_DB_PATH}"

    # Logging
    LOG_PATH: str = os.getenv("LOG_PATH", "app/logs/gateway.log")

    # JWT 認證密鑰
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-tokens-09b25e02930c")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

settings = Settings()

logger.info(f"App Mode: {settings.APP_MODE}")
logger.info(f"Database URL: {settings.SQLALCHEMY_DATABASE_URL}")
