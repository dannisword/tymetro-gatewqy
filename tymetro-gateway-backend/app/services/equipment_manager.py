import time
from typing import Dict, Any, List, Optional
from app.core.logger import logger

class EquipmentManager:
    """
    專門管理 8 台 (及擴充至 32+ 台) PFC200 PLC 設備之狀態：
    - Online / Offline 在線狀態
    - Last Heartbeat 最後心跳時間
    - IP / 韌體版本
    - 即時數值記憶體快取
    """
    def __init__(self):
        # eq_id -> { "equipment_id": str, "name": str, "ip": str, "is_online": bool, "last_heartbeat": float, "firmware": str, "sensors": dict }
        self._equipments: Dict[str, Dict[str, Any]] = {}

    def register_equipment(self, eq_id: str, name: Optional[str] = None, ip: Optional[str] = "127.0.0.1", firmware: str = "v1.0"):
        """初始化註冊設備"""
        if eq_id not in self._equipments:
            self._equipments[eq_id] = {
                "equipment_id": eq_id,
                "name": name or eq_id,
                "ip": ip or "127.0.0.1",
                "is_online": False,
                "last_heartbeat": 0.0,
                "firmware": firmware,
                "sensors": {},
                "sensor_values": {}
            }

    def update_telemetry(self, eq_id: str, payload: Dict[str, Any]):
        """當收到 MQTT/Modbus 遙測數據時更新心跳與數值"""
        now = time.time()
        if eq_id not in self._equipments:
            eq_name = str(payload.get("equipment_name") or payload.get("equipment_id") or eq_id)
            eq_ip = str(payload.get("ip") or "127.0.0.1")
            self.register_equipment(
                eq_id=eq_id,
                name=eq_name,
                ip=eq_ip
            )

        equipment = self._equipments[eq_id]
        equipment["is_online"] = True
        equipment["last_heartbeat"] = now
        if "ip" in payload and payload["ip"]:
            equipment["ip"] = payload["ip"]

        # 更新感測器快取
        if "sensors" in payload:
            equipment["sensors"] = payload["sensors"]
        if "sensor_values" in payload:
            equipment["sensor_values"] = payload["sensor_values"]

    def check_health(self, timeout_sec: float = 60.0) -> List[str]:
        """由 APScheduler 排程定期呼叫：檢查心跳超時，逾時自動標示 Offline"""
        now = time.time()
        offline_equipments = []
        for eq_id, equipment in self._equipments.items():
            if equipment["is_online"]:
                if equipment["last_heartbeat"] > 0 and (now - equipment["last_heartbeat"] > timeout_sec):
                    equipment["is_online"] = False
                    offline_equipments.append(eq_id)
                    logger.warning(f"[EquipmentManager] Equipment {eq_id} heartbeat timed out (> {timeout_sec}s). Status set to OFFLINE.")
        return offline_equipments

    def get_all_equipment_states(self) -> List[Dict[str, Any]]:
        """給 REST API / UI 讀取當前所有設備狀態與心跳"""
        return list(self._equipments.values())

    def get_equipment_state(self, eq_id: str) -> Optional[Dict[str, Any]]:
        return self._equipments.get(eq_id)

equipment_manager = EquipmentManager()
