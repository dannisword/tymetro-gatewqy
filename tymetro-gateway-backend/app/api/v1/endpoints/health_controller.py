import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.core.config import settings
from app.database.session import get_db

router = APIRouter()

START_TIME = time.time()

@router.get("/status", response_model=ResponseBase, summary="獲取閘道器系統與服務狀態 (Health Check)")
def get_gateway_status(db: Session = Depends(get_db)):
    uptime_seconds = int(time.time() - START_TIME)
    
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    data = {
        "gateway_id": settings.GATEWAY_ID,
        "gateway_name": settings.GATEWAY_NAME,
        "app_mode": settings.APP_MODE,
        "status": "online",
        "uptime_seconds": uptime_seconds,
        "services": {
            "sqlite_db": {
                "path": settings.SQLITE_DB_PATH,
                "url": settings.SQLALCHEMY_DATABASE_URL,
                "status": db_status
            },
            "mqtt_broker": {
                "host": settings.MQTT_BROKER_HOST,
                "port": settings.MQTT_BROKER_PORT,
                "status": "connected"  # 初期健康檢查狀態預設為正常
            },
            "modbus_plc": {
                "host": settings.PLC_HOST,
                "port": settings.PLC_PORT,
                "slave_id": settings.PLC_SLAVE_ID,
                "status": "connected"  # 初期健康檢查狀態預設為正常
            }
        },
        "version": "1.0.0",
        "timestamp": int(time.time())
    }
    return ResponseUtil.success(data=data, message="Gateway backend is running normally")
