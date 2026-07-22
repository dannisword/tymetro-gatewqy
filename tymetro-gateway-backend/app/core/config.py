import os
from pydantic_settings import BaseSettings
from app.core.logger import logger

class Settings(BaseSettings):
    APP_MODE: str = os.getenv("APP_MODE", "development")
    GATEWAY_ID: str = os.getenv("GATEWAY_ID", "GW-TYMETRO-001")
    GATEWAY_NAME: str = os.getenv("GATEWAY_NAME", "桃園捷運 IoT Gateway")
    
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", 5400))
    
    # MQTT 設定
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", 1883))
    MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "tymetro_gateway_backend")
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")

    # PLC / Modbus 設定
    PLC_HOST: str = os.getenv("PLC_HOST", "192.168.1.10")
    PLC_PORT: int = int(os.getenv("PLC_PORT", 502))
    PLC_SLAVE_ID: int = int(os.getenv("PLC_SLAVE_ID", 1))

    # 資料庫設定
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "gateway.db")

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"sqlite:///./{self.SQLITE_DB_PATH}"

    # Logging
    LOG_PATH: str = os.getenv("LOG_PATH", "app/logs/gateway.log")

    # JWT 認證
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-tokens-09b25e02930c")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

settings = Settings()

logger.info(f"Gateway ID: {settings.GATEWAY_ID} ({settings.GATEWAY_NAME})")
logger.info(f"App Mode: {settings.APP_MODE}")
logger.info(f"Database URL: {settings.SQLALCHEMY_DATABASE_URL}")
