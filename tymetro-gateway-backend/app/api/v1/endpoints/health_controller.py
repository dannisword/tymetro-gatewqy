import time
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.core.config_yaml import yaml_settings
from app.services.equipment_manager import equipment_manager
from app.core.logger import logger

router = APIRouter()
START_TIME = time.time()

@router.get("/status", response_model=ResponseBase, summary="獲取 Edge Gateway 系統與服務健康度")
async def get_gateway_status():
    """查詢系統健康度與在線設備數"""
    states = equipment_manager.get_all_equipment_states()
    online_count = sum(1 for eq in states if eq.get("is_online"))
    data = {
        "gateway_id": yaml_settings.gateway.id,
        "gateway_name": yaml_settings.gateway.name,
        "location": yaml_settings.gateway.location,
        "status": "online",
        "uptime_seconds": int(time.time() - START_TIME),
        "equipments_monitored": len(states),
        "equipments_online": online_count,
        "version": "1.0.0 (SDS Ready)",
        "timestamp": int(time.time())
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
