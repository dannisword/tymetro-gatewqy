import json
import sqlite3
from typing import List, Dict, Any, Optional
from app.models.config_model import SystemConfig, DeviceConfigModel, RegisterConfigModel
from app.database.session import SessionLocal
from app.core.logger import logger

class DbConfigRepository:
    """提供全系統與 Polling Service 不直接相依 ORM 而是自資料庫快速讀取配置的 Repository"""
    def __init__(self, db_path: str = "gateway.db"):
        self.db_path = db_path

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """自 SQLite 資料庫直接載入所有啟用的 PFC 設備與暫存器點位"""
        db = SessionLocal()
        try:
            devices = db.query(DeviceConfigModel).filter(DeviceConfigModel.is_active == True).all()
            result = []
            for dev in devices:
                regs = [
                    {
                        "name": r.name,
                        "address": r.address,
                        "type": r.data_type,
                        "scale": r.scale,
                        "unit": r.unit
                    }
                    for r in dev.registers
                ]
                result.append({
                    "id": dev.device_id,
                    "name": dev.name,
                    "ip": dev.ip,
                    "port": dev.port,
                    "slave_id": dev.slave_id,
                    "registers": regs
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching devices from DB: {e}")
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
