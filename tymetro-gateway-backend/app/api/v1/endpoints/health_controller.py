import time
import json
import asyncio
import socket
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy import text
from app.database.session import SessionLocal
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.core.config import settings
from app.core.config_yaml import yaml_settings
from app.services.equipment_manager import equipment_manager
from app.services.gateway_mqtt_service import gateway_mqtt_service
from app.services.cloud_mqtt_service import cloud_mqtt_service
from app.services.sqlite_writer import sqlite_writer
from app.services.scheduler_service import scheduler_service
from app.core.logger import logger
from app.database.db_config_repo import db_config_repo
from app.utils.git_version import git_version_info

router = APIRouter()
START_TIME = time.time()

def get_local_ip() -> str:
    """獲取本機對外或區域網路 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

@router.get("/status", response_model=ResponseBase, summary="獲取 Edge Gateway 系統與服務健康度")
async def get_gateway_status():
    """查詢系統健康度、在線設備數與各核心服務狀態"""
    states = equipment_manager.get_all_equipment_states()
    online_count = sum(1 for eq in states if eq.get("is_online"))

    # 1. SQLite 資料庫健康度
    db_status = "connected"
    db_msg = "資料庫連線正常"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_msg = f"資料庫異常: {e}"

    # 2. 設備端 MQTT (Local Broker)
    if not yaml_settings.network.gateway_mqtt.enabled:
        gw_mqtt_status = "stopped"
        gw_mqtt_msg = "服務未啟用 (gateway.yaml)"
    elif getattr(gateway_mqtt_service, "is_connected", False):
        gw_mqtt_status = "connected"
        gw_mqtt_msg = f"已連線至設備端 Broker ({gateway_mqtt_service.host}:{gateway_mqtt_service.port})"
    elif getattr(gateway_mqtt_service, "_running", False):
        gw_mqtt_status = "disconnected"
        gw_mqtt_msg = f"連線中 / 嘗試重連至 {gateway_mqtt_service.host}:{gateway_mqtt_service.port}"
    else:
        gw_mqtt_status = "stopped"
        gw_mqtt_msg = "服務已停止"

    # 3. 桃捷雲 MQTT (Cloud MQTT Forwarder)
    if not yaml_settings.network.cloud_mqtt.enabled:
        cloud_mqtt_status = "stopped"
        cloud_mqtt_msg = "服務未啟用 (gateway.yaml)"
    elif getattr(cloud_mqtt_service, "is_connected", False):
        cloud_mqtt_status = "connected"
        cloud_mqtt_msg = f"已連線至桃捷雲 Broker ({cloud_mqtt_service.cloud_host}:{cloud_mqtt_service.cloud_port})"
    elif getattr(cloud_mqtt_service, "_running", False):
        cloud_mqtt_status = "disconnected"
        cloud_mqtt_msg = f"連線中 / 嘗試重連至 {cloud_mqtt_service.cloud_host}:{cloud_mqtt_service.cloud_port}"
    else:
        cloud_mqtt_status = "stopped"
        cloud_mqtt_msg = "服務已停止"

    # 4. 背景排程服務 (APScheduler)
    scheduler_running = scheduler_service.scheduler.running if hasattr(scheduler_service, "scheduler") else False
    scheduler_status = "running" if scheduler_running else "stopped"
    scheduler_msg = "排程引擎運行中 (心跳檢測 / 定期備份 / 日誌清理)" if scheduler_running else "排程服務已停止"

    # 5. SQLite 批次寫入器
    writer_running = getattr(sqlite_writer, "_running", False)
    writer_status = "running" if writer_running else "stopped"
    queue_size = sqlite_writer.queue.qsize() if hasattr(sqlite_writer, "queue") else 0
    writer_msg = f"批次寫入隊列中 (暫存緩衝: {queue_size} 筆)" if writer_running else "批次寫入器已停止"

    services = {
        "sqlite_db": {
            "name": "SQLite 資料庫",
            "status": db_status,
            "path": settings.SQLITE_DB_PATH,
            "url": settings.SQLALCHEMY_DATABASE_URL,
            "message": db_msg
        },
        "gateway_mqtt": {
            "name": "設備端 MQTT (Broker)",
            "status": gw_mqtt_status,
            "host": getattr(gateway_mqtt_service, "host", yaml_settings.network.gateway_mqtt.broker_host),
            "port": getattr(gateway_mqtt_service, "port", yaml_settings.network.gateway_mqtt.broker_port),
            "message": gw_mqtt_msg
        },
        "cloud_mqtt": {
            "name": "桃捷雲 MQTT (Forwarder)",
            "status": cloud_mqtt_status,
            "host": getattr(cloud_mqtt_service, "cloud_host", yaml_settings.network.cloud_mqtt.broker_host),
            "port": getattr(cloud_mqtt_service, "cloud_port", yaml_settings.network.cloud_mqtt.broker_port),
            "message": cloud_mqtt_msg
        },
        "scheduler": {
            "name": "排程服務 (Scheduler)",
            "status": scheduler_status,
            "message": scheduler_msg
        },
        "sqlite_writer": {
            "name": "批次寫入器 (Batch Writer)",
            "status": writer_status,
            "message": writer_msg
        }
    }

    data = {
        "gateway_id": db_config_repo.get_system_config("gateway.id") or yaml_settings.gateway.id,
        "gateway_name": db_config_repo.get_system_config("gateway.name") or yaml_settings.gateway.name,
        "location": db_config_repo.get_system_config("gateway.location") or yaml_settings.gateway.location,
        "app_mode": settings.APP_MODE,
        "local_ip": get_local_ip(),
        "status": "online",
        "uptime_seconds": int(time.time() - START_TIME),
        "equipments_monitored": len(states),
        "equipments_online": online_count,
        "version": "1.0.0 (SDS Ready)",
        "git_version": git_version_info,
        "timestamp": int(time.time()),
        "services": services
    }
    return ResponseUtil.success(data=data, message="Gateway health check succeeded")

@router.get("/realtime", response_model=ResponseBase, summary="查詢記憶體即時資料")
async def get_realtime_data(equipment_id: str = Query(None, description="指定設備 ID (如 1)")):
    """直接從 EquipmentManager 記憶體快取獲取最新採樣數值"""
    if equipment_id:
        eq_state = equipment_manager.get_equipment_state(equipment_id)
        return ResponseUtil.success(data=eq_state, message="Equipment realtime data retrieved")
    
    states = equipment_manager.get_all_equipment_states()
    return ResponseUtil.success(data=states, message="Realtime data retrieved successfully")

@router.websocket("/ws/diff")
async def websocket_diff_endpoint(websocket: WebSocket):
    """Native WebSocket 差分推播 (Diff Push)"""
    await websocket.accept()
    logger.info("WebSocket client connected for Diff Push.")
    last_pushed_cache: Dict[str, Any] = {}

    try:
        while True:
            states = equipment_manager.get_all_equipment_states()
            current_cache: Dict[str, Any] = {
                str(eq["equipment_id"]): eq
                for eq in states
                if "equipment_id" in eq and eq["equipment_id"] is not None
            }
            diffs = {}

            for dev_id, dev_data in current_cache.items():
                if dev_id is not None:
                    old_data = last_pushed_cache.get(dev_id)
                    if not old_data or dev_data != old_data:
                        diffs[dev_id] = dev_data

            if diffs:
                await websocket.send_json({
                    "type": "diff",
                    "timestamp": time.time(),
                    "data": diffs
                })
                last_pushed_cache = json.loads(json.dumps(current_cache))
            else:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": time.time()
                })

            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
