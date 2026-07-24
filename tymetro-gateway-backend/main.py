import asyncio
from fastapi import FastAPI, HTTPException, Request 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.middleware.logging_middleware import LoggingMiddleware
from app.core.config_yaml import yaml_settings
from app.core.config import settings
from app.core.logger import logger
from app.api.v1.api import api_router
from app.database.session import SessionLocal
from app.database.init_db import create_tables, init_mock_data
from app.services.sqlite_writer import sqlite_writer
from app.services.mqtt_service import mqtt_service
from app.services.cloud_mqtt_service import cloud_mqtt_service
from app.services.scheduler_service import scheduler_service
import app.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【啟動階段】
    logger.info(f"Gateway Application starting up SDS Mode...")
    logger.info(f"Gateway ID: {yaml_settings.gateway.id} | Name: {yaml_settings.gateway.name}")
    try:
        create_tables()
        db = SessionLocal()
        try:
            init_mock_data(db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating database tables or initializing mock data: {e}")

    # 1. 啟動 SQLite 佇列批次寫入器 (SQLite Batch Writer)
    await sqlite_writer.start()

    # 2. 啟動 MQTT 訂閱服務 (MQTT Subscriber Service)
    if yaml_settings.network.mqtt.enabled:
        await mqtt_service.start()
    else:
        logger.info("[MQTTService] MQTT Service is disabled in gateway.yaml.")

    # 3. 啟動 桃捷雲 Cloud MQTT 拋轉服務 (Cloud MQTT Forwarder Service)
    if yaml_settings.network.cloud_mqtt.enabled:
        await cloud_mqtt_service.start()
    else:
        logger.info("[CloudMQTTService] Cloud MQTT Forwarder is disabled in gateway.yaml.")

    # 4. 啟動 APScheduler 背景定期排程 (Heartbeat Check & Daily Backup)
    scheduler_service.start()
    
    yield

    # 【關閉階段】
    logger.info("Gateway Application shutting down...")
    scheduler_service.stop()
    if yaml_settings.network.cloud_mqtt.enabled:
        await cloud_mqtt_service.stop()
    if yaml_settings.network.mqtt.enabled:
        await mqtt_service.stop()
    await sqlite_writer.stop()

app = FastAPI(title=f"tymetro-gateway ({yaml_settings.gateway.id})", lifespan=lifespan)

# 掛載中介軟體
app.add_middleware(LoggingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "total": 0,
            "data": None
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """捕捉 Pydantic 參數驗證錯誤"""
    errors = exc.errors()
    msg = f"參數驗證失敗: {errors[0].get('msg')} (欄位: {errors[0].get('loc')})" if errors else "參數格式錯誤"
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": msg,
            "total": 0,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    """捕捉所有未處理的系統異常 (500)"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"伺服器內部錯誤: {str(exc)}",
            "total": 0,
            "data": None
        }
    )

# 註冊 API 路由 (v1)
app.include_router(api_router, prefix="/api/v1")
