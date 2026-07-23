import json
import sqlite3
from typing import List, Dict, Any, Optional
from app.models.config_model import SystemConfig
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.database.session import SessionLocal
from app.core.logger import logger

class DbConfigRepository:
    """提供全系統與 Polling Service 不直接相依 ORM 而是自資料庫快速讀取配置的 Repository"""
    def __init__(self, db_path: str = "gateway.db"):
        self.db_path = db_path

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """自 SQLite 資料庫載入所有啟用的設備與其 REAL_TIME 類型的感測器/點位"""
        db = SessionLocal()
        try:
            equipments = db.query(Equipment).filter(Equipment.isActive == True).all()
            result = []
            for eq in equipments:
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
                        "value": s.sensorValue
                    })

                result.append({
                    "id": eq.equipmentName,
                    "name": eq.equipmentName,
                    "ip": eq.ipAddress or "127.0.0.1",
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

db_config_repo = DbConfigRepository()
