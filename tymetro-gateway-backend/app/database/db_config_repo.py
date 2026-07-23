import json
import sqlite3
from typing import List, Dict, Any, Optional
from app.models.config_model import SystemConfig
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.database.session import SessionLocal
from app.core.config import settings
from app.core.logger import logger


class DbConfigRepository:
    """提供全系統與 Polling Service 不直接相依 ORM 而是自資料庫快速讀取配置的 Repository"""
    def __init__(self, db_path: str = "gateway.db"):
        self.db_path = db_path
        # 記憶體快取 (RAM Cache): (car_vin, end_pos) -> eq_info (O(1) 超高效能對照)
        self._equipment_cache: Dict[Any, Dict[str, Any]] = {}

    def get_all_equipments(self) -> List[Dict[str, Any]]:
        """自 SQLite 資料庫載入所有啟用的設備與其 REAL_TIME 類型的感測器/點位，並預熱快取"""
        db = SessionLocal()
        try:
            from app.models.car_model import Car
            equipments = db.query(Equipment).filter(Equipment.isActive == True).all()
            result = []
            for eq in equipments:
                # 自動預熱快取 (Pre-warm RAM Cache): (car_vin, end_pos) -> eq_info
                car = db.query(Car).filter(Car.id == eq.carId).first()
                if car and car.carVin:
                    cache_key = (str(car.carVin), eq.endPos)
                    self._equipment_cache[cache_key] = {
                        "eq_id": str(eq.id or eq.equipmentName),
                        "equipment_name": eq.equipmentName
                    }

                sensors = db.query(Sensor).filter(
                    Sensor.equipmentId == eq.id,
                    Sensor.sensorType == "REAL_TIME",
                    Sensor.isActive == True
                ).all()

                regs = []
                for s in sensors:
                    addr = 0
                    if s.sensorCode and s.sensorCode.startswith("D") and s.sensorCode[1:].isdigit():
                        addr = int(s.sensorCode[1:])
                    
                    regs.append({
                        "code": s.sensorCode,
                        "name": s.sensorName,
                        "address": addr,
                        "type": "INT16",
                        "scale": 1.0,
                        "unit": s.sensorUnit,
                        "sensor_type": s.sensorType,
                        "value": s.sensorValue,
                        "car_id": s.carId
                    })

                ip = eq.ipAddress or "127.0.0.1"
                if settings.PLC_IP_SUBNET and ip != "127.0.0.1":
                    parts = ip.split(".")
                    if len(parts) == 4:
                        ip = f"{settings.PLC_IP_SUBNET}.{parts[-1]}"
                        #logger.info(f"IP Address modified for {eq.equipmentName}: {ip}")

                result.append({
                    "id": eq.equipmentName,
                    "name": eq.equipmentName,
                    "ip": ip,
                    "port": 502,
                    "slave_id": 1,
                    "registers": regs
                })

            return result
        except Exception as e:
            logger.error(f"Error fetching equipments and sensors from DB: {e}")
            return []
        finally:
            db.close()

    def get_system_config(self, key: str, default: Any = None) -> Any:
        db = SessionLocal()
        try:
            cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if cfg:
                return cfg.value
            return default
        except Exception as e:
            logger.error(f"Error fetching config key {key} from DB: {e}")
            return default
        finally:
            db.close()

    def update_sensor_values(self, updates: Dict[str, float]):
        """批量更新感測器即時數值 (sensorValue) 至 SQLite sensors 資料表"""
        if not updates:
            return
        db = SessionLocal()
        try:
            for code, val in updates.items():
                db.query(Sensor).filter(Sensor.sensorCode == code).update(
                    {Sensor.sensorValue: val},
                    synchronize_session=False
                )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating sensor values to DB: {e}")
        finally:
            db.close()

    def get_equipment_by_vin_and_pos(self, car_vin: Optional[str], end_pos: Optional[int]) -> Dict[str, Any]:
        """根據 car_vin 與 end_pos 自記憶體快取或 SQLite 資料庫快速對照查詢 (O(1) 高效能)"""
        if not car_vin:
            return {"eq_id": "PFC200", "equipment_name": "PFC200"}
        
        cache_key = (str(car_vin), end_pos)
        # 1. 命中記憶體快取 (RAM Dict Cache): O(1) 複雜度，極速回傳且 0 次 Disk IO
        if cache_key in self._equipment_cache:
            return self._equipment_cache[cache_key]

        # 2. 首次未命中：連線 SQLite 開啟 JOIN 查詢並寫入記憶體快取
        db = SessionLocal()
        try:
            from app.models.car_model import Car
            query = db.query(Equipment).join(Car, Equipment.carId == Car.id).filter(Car.carVin == str(car_vin))
            if end_pos is not None:
                query = query.filter(Equipment.endPos == int(end_pos))
            
            eq = query.first()
            if eq:
                info = {
                    "eq_id": str(eq.id or eq.equipmentName or car_vin),
                    "equipment_name": eq.equipmentName or f"{car_vin}_{end_pos}"
                }
            else:
                default_name = f"{car_vin}_{end_pos}" if end_pos is not None else car_vin
                info = {
                    "eq_id": default_name,
                    "equipment_name": default_name
                }
            
            self._equipment_cache[cache_key] = info
            return info
        except Exception as e:
            logger.error(f"Error querying equipment info from SQLite: {e}")
            default_name = f"{car_vin}_{end_pos}" if end_pos is not None else str(car_vin)
            return {"eq_id": default_name, "equipment_name": default_name}
        finally:
            db.close()

db_config_repo = DbConfigRepository()
