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

    def register_equipment(
        self,
        eq_id: str,
        name: Optional[str] = None,
        ip: Optional[str] = "127.0.0.1",
        firmware: str = "v1.0",
        train_no: Optional[str] = None,
        car_vin: Optional[str] = None,
        end_pos: Optional[int] = None
    ):
        """初始化註冊設備 (包含車組 train_no、車廂 car_vin、端點 end_pos)"""
        if eq_id not in self._equipments:
            self._equipments[eq_id] = {
                "equipment_id": eq_id,
                "name": name or eq_id,
                "ip": ip or "127.0.0.1",
                "is_online": False,
                "last_heartbeat": 0.0,
                "firmware": firmware,
                "train_no": train_no,
                "car_vin": car_vin,
                "end_pos": end_pos,
                "sensors": {}
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
                ip=eq_ip,
                train_no=payload.get("train_no") or payload.get("trainNo"),
                car_vin=payload.get("car_vin") or payload.get("carVin"),
                end_pos=payload.get("end_pos") or payload.get("endPos")
            )

        equipment = self._equipments[eq_id]
        equipment["is_online"] = True
        equipment["last_heartbeat"] = now
        if "ip" in payload and payload["ip"]:
            equipment["ip"] = payload["ip"]
        if "train_no" in payload and payload["train_no"]:
            equipment["train_no"] = payload["train_no"]
        elif "trainNo" in payload and payload["trainNo"]:
            equipment["train_no"] = payload["trainNo"]
        if "car_vin" in payload and payload["car_vin"]:
            equipment["car_vin"] = payload["car_vin"]
        elif "carVin" in payload and payload["carVin"]:
            equipment["car_vin"] = payload["carVin"]
        if "end_pos" in payload and payload["end_pos"] is not None:
            equipment["end_pos"] = payload["end_pos"]
        elif "endPos" in payload and payload["endPos"] is not None:
            equipment["end_pos"] = payload["endPos"]

        # 更新感測器快取 (僅保留單一 sensors 欄位)
        if "sensors" in payload:
            equipment["sensors"] = payload["sensors"]
        elif "sensor_values" in payload:
            equipment["sensors"] = payload["sensor_values"]

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
        """給 REST API / UI 讀取當前所有設備狀態與心跳 (包含 Unix 時間戳記與人類可讀時間)"""
        from datetime import datetime
        result = []
        for eq in self._equipments.values():
            item = dict(eq)
            ts = item.get("last_heartbeat", 0.0)
            if ts and ts > 0:
                item["last_heartbeat_time"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            else:
                item["last_heartbeat_time"] = None
            result.append(item)
        return result

    def get_equipment_state(self, eq_id: str) -> Optional[Dict[str, Any]]:
        return self._equipments.get(eq_id)

equipment_manager = EquipmentManager()
