import time
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.core.config_yaml import yaml_settings
from app.ipc.client import ipc_client
from app.core.logger import logger

router = APIRouter()
START_TIME = time.time()

@router.get("/status", response_model=ResponseBase, summary="透過 IPC 獲取 Edge Gateway 系統與服務健康度")
async def get_gateway_status():
    """使用 Unix Domain Socket 向 polling.service 查詢系統健康度"""
    ipc_resp = await ipc_client.send_command("GET_SYSTEM_HEALTH")
    
    if ipc_resp.get("code") == 200:
        health_data = ipc_resp.get("data", {})
        data = {
            "gateway_id": yaml_settings.gateway.id,
            "gateway_name": yaml_settings.gateway.name,
            "location": yaml_settings.gateway.location,
            "status": "online",
            "uptime_seconds": int(time.time() - START_TIME),
            "ipc_status": "connected",
            "central_server_connected": health_data.get("central_connected", False),
            "equipments_monitored": len(yaml_settings.equipments),
            "version": "1.0.0 (SDS Ready)",
            "timestamp": int(time.time())
        }
        return ResponseUtil.success(data=data, message="Gateway health check via IPC succeeded")
    else:
        return ResponseUtil.error(message=f"IPC Health Check Failed: {ipc_resp.get('msg')}", code=503)

@router.get("/realtime", response_model=ResponseBase, summary="透過 IPC 查詢記憶體即時資料")
async def get_realtime_data(equipment_id: str = Query(None, description="指定設備 ID (如 PFC11011)")):
    """透過 Unix Domain Socket 不經資料庫直接從記憶體快取獲取最新採樣數值"""
    params = {"equipment_id": equipment_id} if equipment_id else {}
    ipc_resp = await ipc_client.send_command("GET_REALTIME", params=params)

    
    if ipc_resp.get("code") == 200:
        return ResponseUtil.success(data=ipc_resp.get("data"), message="Realtime data retrieved via IPC")
    else:
        return ResponseUtil.error(message=f"IPC Query Failed: {ipc_resp.get('msg')}", code=500)

@router.websocket("/ws/diff")
async def websocket_diff_endpoint(websocket: WebSocket):
    """
    Native WebSocket 差分推播 (Diff Push)
    僅在數據發生變化或警報時推播完整差分報文，無變化時推播極小的 Heartbeat (心跳包)。
    能節省 PFC 200 近 50% CPU 序列化開銷。
    """
    await websocket.accept()
    logger.info("WebSocket client connected for Diff Push.")
    last_pushed_cache: Dict[str, Any] = {}

    try:
        while True:
            ipc_resp = await ipc_client.send_command("GET_REALTIME")
            if ipc_resp.get("code") == 200:
                current_cache = ipc_resp.get("data", {})
                diffs = {}

                # 差分比較 (Diff Calculation)
                for dev_id, dev_data in current_cache.items():
                    old_data = last_pushed_cache.get(dev_id)
                    if not old_data:
                        diffs[dev_id] = dev_data
                    else:
                        # 檢查數值變動或 Alarm 變動
                        if (dev_data.get("temp") != old_data.get("temp") or
                            dev_data.get("humidity") != old_data.get("humidity") or
                            dev_data.get("alarm_status") != old_data.get("alarm_status")):
                            diffs[dev_id] = dev_data

                if diffs:
                    # 發送增量 (Diff)
                    await websocket.send_json({
                        "type": "diff",
                        "timestamp": time.time(),
                        "data": diffs
                    })
                    last_pushed_cache = json.loads(json.dumps(current_cache))
                else:
                    # 無變化發送極簡 Heartbeat (心跳包)
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": time.time()
                    })

            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
