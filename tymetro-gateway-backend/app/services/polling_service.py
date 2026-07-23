import asyncio
import time
import random
from typing import Dict, Any, Optional, List
from app.core.logger import logger
from app.ipc.server import IPCServer
from app.database.outbox import init_outbox_table
from app.database.db_config_repo import db_config_repo
from app.services.central_client import central_tcp_client

class MemoryCache:
    """記憶體快取核心，不直接寫入 SQLite 避免硬碟磨損"""
    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.cached_device_configs: List[Dict[str, Any]] = []
        self.gateway_id: str = "GW-TAU-01"
        self.last_update: float = 0.0

    def reload_configs(self):
        """熱加載 (Hot Reload)：從 SQLite DB 刷新內存中的 PFC 設備與暫存器點位配置"""
        self.cached_device_configs = db_config_repo.get_all_devices()
        self.gateway_id = db_config_repo.get_system_config("gateway.id", "GW-TAU-01")
        logger.info(f"MemoryCache Hot Reloaded from DB: {len(self.cached_device_configs)} active devices.")

    def update_device(self, device_id: str, data: Dict[str, Any]):
        self.devices[device_id] = {
            **data,
            "updated_at": time.time()
        }
        self.last_update = time.time()

    def get_realtime(self, device_id: Optional[str] = None) -> Any:
        if device_id:
            return self.devices.get(device_id)
        return self.devices

memory_cache = MemoryCache()

async def ipc_request_handler(req_id: Optional[int], cmd: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """處理來自 API Service 的 IPC 指令"""
    if cmd == "GET_REALTIME":
        dev_id = params.get("device_id")
        data = memory_cache.get_realtime(dev_id)
        return {"id": req_id, "code": 200, "msg": "OK", "data": data}
    
    elif cmd == "GET_ALL_DEVICES":
        return {"id": req_id, "code": 200, "msg": "OK", "data": memory_cache.cached_device_configs}

    elif cmd == "RELOAD_CONFIG":
        """接收 DB 變更後的 Hot Reload 通知指令"""
        memory_cache.reload_configs()
        return {"id": req_id, "code": 200, "msg": "Config Reloaded Successfully", "data": {"device_count": len(memory_cache.cached_device_configs)}}

    elif cmd == "GET_SYSTEM_HEALTH":
        return {
            "id": req_id,
            "code": 200,
            "msg": "OK",
            "data": {
                "gateway_id": memory_cache.gateway_id,
                "central_connected": central_tcp_client.is_connected,
                "memory_devices_count": len(memory_cache.devices),
                "last_update": memory_cache.last_update,
                "uptime": time.time()
            }
        }

    return {"id": req_id, "code": 404, "msg": f"Unknown Command: {cmd}", "data": None}

class PollingService:
    def __init__(self):
        self.ipc_server = IPCServer(handler_func=ipc_request_handler)
        self._running = False

    async def start(self):
        self._running = True
        init_outbox_table()
        # 從 DB 刷新配置
        memory_cache.reload_configs()
        await self.ipc_server.start()
        await central_tcp_client.start_loop()
        asyncio.create_task(self._poll_loop())
        logger.info("Polling Service started successfully with DB configs.")

    async def _poll_loop(self):
        while self._running:
            try:
                # 動態自 memory_cache 讀取從 DB 載入的 PFC 設備清單
                devices = memory_cache.cached_device_configs
                for dev in devices:
                    dev_id = dev.get("id")
                    if not dev_id:
                        continue

                    simulated_temp = round(24.0 + random.uniform(-0.5, 0.5), 1)
                    simulated_humidity = round(60.0 + random.uniform(-1.0, 1.0), 1)
                    
                    data = {
                        "device_id": dev_id,
                        "name": dev.get("name"),
                        "ip": dev.get("ip"),
                        "temp": simulated_temp,
                        "humidity": simulated_humidity,
                        "alarm_status": 0,
                        "timestamp": time.time()
                    }
                    
                    # 1. 更新記憶體快取
                    memory_cache.update_device(dev_id, data)

                    # 2. 推播至中央伺服器 (若斷網會自動寫入 Outbox)
                    await central_tcp_client.send_payload({
                        "gateway_id": memory_cache.gateway_id,
                        "type": "telemetry",
                        "data": data
                    })

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            await asyncio.sleep(1.0)

    async def stop(self):
        self._running = False
        await central_tcp_client.stop()
        await self.ipc_server.stop()
        logger.info("Polling Service stopped.")

polling_service = PollingService()
