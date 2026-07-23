import asyncio
import time
from typing import Dict, Any, Optional, List
from app.core.logger import logger
from app.ipc.server import IPCServer
from app.database.db_config_repo import db_config_repo
from app.repositories.outbox_repository import outbox_repo
from app.repositories.sensor_history_repository import sensor_history_repo
from app.services.central_client import central_tcp_client

try:
    import logging
    from pymodbus.client import AsyncModbusTcpClient
    logging.getLogger("pymodbus").setLevel(logging.ERROR)
    MODBUS_AVAILABLE = True
except ImportError:
    AsyncModbusTcpClient = None
    MODBUS_AVAILABLE = False

class MemoryCache:
    """記憶體快取核心，不直接寫入 SQLite 避免硬碟磨損"""
    def __init__(self):
        self.equipments: Dict[str, Dict[str, Any]] = {}
        self.cached_equipment_configs: List[Dict[str, Any]] = []
        self.gateway_id: str = "GW-TAU-01"
        self.last_update: float = 0.0

    def reload_configs(self):
        """熱加載 (Hot Reload)：從 SQLite DB 刷新內存中的 PFC 設備配置 (equipments)"""
        self.cached_equipment_configs = db_config_repo.get_all_equipments()
        self.gateway_id = db_config_repo.get_system_config("gateway.id", "GW-TAU-01")
        logger.info(f"MemoryCache Hot Reloaded from DB: {len(self.cached_equipment_configs)} active equipments.")

    def update_equipment(self, equipment_id: str, data: Dict[str, Any]):
        self.equipments[equipment_id] = {
            **data,
            "updated_at": time.time()
        }
        self.last_update = time.time()


    def get_realtime(self, equipment_id: Optional[str] = None) -> Any:
        if equipment_id:
            return self.equipments.get(equipment_id)
        return self.equipments

memory_cache = MemoryCache()

async def ipc_request_handler(req_id: Optional[int], cmd: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """處理來自 API Service 的 IPC 指令"""
    if cmd == "GET_REALTIME":
        eq_id = params.get("equipment_id") or params.get("device_id")
        data = memory_cache.get_realtime(eq_id)
        return {"id": req_id, "code": 200, "msg": "OK", "data": data}
    
    elif cmd in ("GET_ALL_EQUIPMENTS", "GET_ALL_DEVICES"):
        return {"id": req_id, "code": 200, "msg": "OK", "data": memory_cache.cached_equipment_configs}

    elif cmd == "RELOAD_CONFIG":
        """接收 DB 變更後的 Hot Reload 通知指令"""
        memory_cache.reload_configs()
        return {"id": req_id, "code": 200, "msg": "Config Reloaded Successfully", "data": {"equipment_count": len(memory_cache.cached_equipment_configs)}}

    elif cmd == "GET_SYSTEM_HEALTH":
        return {
            "id": req_id,
            "code": 200,
            "msg": "OK",
            "data": {
                "gateway_id": memory_cache.gateway_id,
                "central_connected": False, # central_client 已暫停
                "memory_equipments_count": len(memory_cache.equipments),
                "last_update": memory_cache.last_update,
                "uptime": time.time()
            }
        }

    return {"id": req_id, "code": 404, "msg": f"Unknown Command: {cmd}", "data": None}

class PollingService:
    def __init__(self, batch_size: int = 1000):
        self.ipc_server = IPCServer(handler_func=ipc_request_handler)
        self._running = False
        # 長連線池: equipment_id -> AsyncModbusTcpClient
        self._modbus_clients: Dict[str, Any] = {}
        # 歷史紀錄記憶體 Queue 暫存區 (達到 1000 筆批量寫入 DB)
        self._history_queue: List[Dict[str, Any]] = []
        self._batch_size: int = batch_size

    def _flush_history_queue(self):
        """將記憶體中暫存的歷史紀錄一次性批量寫入 SensorHistory 與 Outbox 資料庫"""
        if not self._history_queue:
            return
        items_to_flush = list(self._history_queue)
        self._history_queue.clear()
        
        # 1. 批量寫入感測器歷史紀錄表 (sensor_histories)
        sensor_history_repo.add_batch(items_to_flush)

        # 2. 批量寫入離線補傳佇列 (outbox)
        outbox_repo.push_batch(items_to_flush)

        logger.info(f"Flushed {len(items_to_flush)} sensor history records into DB (Batch Mode).")

    async def _get_modbus_client(self, eq_id: str, ip: str, port: int) -> Optional[Any]:
        """維護 Modbus TCP 長連線 (Persistent Connection)"""
        if AsyncModbusTcpClient is None:
            logger.warning("[Modbus Debug] pymodbus library is not installed or available.")
            return None

        client = self._modbus_clients.get(eq_id)
        
        # 1. 若已有連線，檢查狀態
        if client:
            if getattr(client, 'connected', False):
                return client
            # 已經中斷連線，進行關閉清理
            try:
                client.close()
            except Exception:
                pass
            self._modbus_clients.pop(eq_id, None)

        # 2. 建立新長連線
        try:
            logger.info(f"[Modbus Debug] Attempting to connect Modbus TCP for {eq_id} ({ip}:{port})...")
            new_client = AsyncModbusTcpClient(ip, port=port, timeout=1.5)
            if await new_client.connect():
                logger.info(f"[Modbus Debug] Successfully connected Modbus TCP for {eq_id} ({ip}:{port}).")
                self._modbus_clients[eq_id] = new_client
                return new_client
            else:
                logger.warning(f"[Modbus Debug] Failed to connect Modbus TCP for {eq_id} ({ip}:{port}) - Socket refused/timeout.")
        except Exception as e:
            logger.warning(f"[Modbus Debug] Connection exception for {eq_id} ({ip}:{port}): {e}")

        return None

    async def start(self):
        self._running = True
        # 從 DB 刷新配置
        memory_cache.reload_configs()
        await self.ipc_server.start()
        # 暫停連線中央伺服器與 Outbox 補傳
        # await central_tcp_client.start_loop()
        
        # 啟動定期輪詢任務
        asyncio.create_task(self._poll_loop())
        logger.info("Polling Service started successfully with DB configs.")

    async def _poll_loop(self):
        while self._running:
            try:
                # 動態自 memory_cache 讀取從 DB 載入的 PFC 設備清單 (equipments)
                equipments = memory_cache.cached_equipment_configs

                for eq in equipments:
                    eq_id = eq.get("id")
                    if not eq_id:
                        continue

                    protocol = eq.get("protocol", "MODBUS_TCP")
                    if protocol.upper() == "MQTT":
                        # 此設備設定為 MQTT 通訊協定，由 MQTTService 發起 Sub 非同步接收，跳過 Modbus TCP Polling
                        continue

                    ip = eq.get("ip", "127.0.0.1")
                    port = eq.get("port", 502)
                    slave_id = eq.get("slave_id", 1)
                    registers = eq.get("registers", [])

                    modbus_success = False
                    sensor_values: Dict[str, Any] = {}
                    updated_sensors: List[Dict[str, Any]] = []

                    if len(registers) == 0:
                        logger.warning(f"[Modbus Debug] Equipment {eq_id} ({ip}:{port}) has 0 registers configured.")

                    # 1. 重用/維護長連線發起 Modbus TCP 讀取
                    if AsyncModbusTcpClient is not None and ip and ip != "127.0.0.1":
                        client = await self._get_modbus_client(eq_id, ip, port)
                        if client:
                            try:
                                for reg in registers:
                                    code = reg.get("code")
                                    raw_addr = reg.get("address", 0)
                                    scale = reg.get("scale", 1.0)
                                    
                                    # Modbus 5位數表記轉 0-based 位址偏移量 (40001 -> 0, 40009 -> 8)
                                    modbus_addr = raw_addr
                                    if modbus_addr >= 40001:
                                        modbus_addr -= 40001
                                    elif modbus_addr >= 40000:
                                        modbus_addr -= 40000

                                    res = await client.read_holding_registers(address=modbus_addr, count=1, device_id=slave_id)
                                    if not res.isError() and hasattr(res, 'registers') and len(res.registers) > 0:
                                        raw_val = res.registers[0]
                                        if raw_val > 32767:
                                            raw_val -= 65536
                                        val = round(raw_val * scale, 2)
                                        logger.info(f"[Modbus Debug] {eq_id} ({ip}) READ SUCCESS -> code={code}, raw_addr={raw_addr}, offset={modbus_addr}, raw={raw_val}, val={val}")
                                    else:
                                        val = reg.get("value")
                                        logger.warning(f"[Modbus Debug] {eq_id} ({ip}) READ ERROR -> code={code}, raw_addr={raw_addr}, offset={modbus_addr}, response={res}")
                                    
                                    sensor_item = {**reg, "value": val}
                                    updated_sensors.append(sensor_item)
                                    if code:
                                        sensor_values[code] = val

                                modbus_success = True
                            except Exception as read_err:
                                logger.warning(f"[Modbus Debug] Read Exception for {eq_id} ({ip}:{port}): {read_err}")
                                try:
                                    client.close()
                                except Exception:
                                    pass
                                self._modbus_clients.pop(eq_id, None)

                    # 2. 若 Modbus 連線/讀取未成功，僅保持資料結構
                    if not modbus_success:
                        for reg in registers:
                            code = reg.get("code", "")
                            val = reg.get("value")
                            sensor_item = {**reg, "value": val}
                            updated_sensors.append(sensor_item)
                            if code and val is not None:
                                sensor_values[code] = val

                    # 3. 組裝更新後的設備結構
                    data = {
                        "equipment_id": eq_id,
                        "name": eq.get("name"),
                        "ip": ip,
                        "port": port,
                        "slave_id": slave_id,
                        "modbus_connected": modbus_success,
                        "sensors": updated_sensors,
                        "sensor_values": sensor_values,
                        "timestamp": time.time()
                    }
                    
                    # 4. 更新記憶體快取
                    memory_cache.update_equipment(eq_id, data)

                    # 5. 僅在 Modbus 成功讀取到實體數據時，更新 SQLite sensors 即時數值與寫入歷史紀錄 Queue
                    if modbus_success and sensor_values:
                        db_config_repo.update_sensor_values(sensor_values)

                        for s_item in updated_sensors:
                            self._history_queue.append({
                                "car_id": s_item.get("car_id", 0),
                                "car_vin": s_item.get("car_vin"),
                                "car_no": s_item.get("car_no"),
                                "end_pos": s_item.get("end_pos"),
                                "sensor_code": s_item.get("code", ""),
                                "sensor_value": s_item.get("value", 0.0),
                                "recorded_at": data["timestamp"],
                                "sensor_name": s_item.get("name"),
                                "sensor_unit": s_item.get("unit"),
                                "equipment_name": eq.get("name")
                            })

                        # 滿 1000 筆時批量寫入 DB
                        if len(self._history_queue) >= self._batch_size:
                            self._flush_history_queue()

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            await asyncio.sleep(1.0)

    async def stop(self):
        self._running = False

        # 1. 清空刷新剩餘未滿 1000 筆的歷史紀錄寫入 Outbox DB
        self._flush_history_queue()

        # 2. 關閉所有 Modbus TCP 長連線
        for eq_id, client in list(self._modbus_clients.items()):
            try:
                client.close()
            except Exception:
                pass
        self._modbus_clients.clear()

        # await central_tcp_client.stop()
        await self.ipc_server.stop()
        logger.info("Polling Service stopped.")

polling_service = PollingService()


