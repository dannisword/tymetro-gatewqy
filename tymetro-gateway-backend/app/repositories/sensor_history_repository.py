from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.sensor_history_model import SensorHistory
from app.database.session import SessionLocal
from app.core.logger import logger

class SensorHistoryRepository(BaseRepository[SensorHistory]):
    """感測器歷史資料 Repository"""
    def __init__(self, db: Optional[Session] = None):
        self._external_db = db is not None
        session = db or SessionLocal()
        super().__init__(SensorHistory, session)

    def add_batch(self, items: List[Dict[str, Any]]) -> bool:
        """寫入批量感測器歷史紀錄，單一 Transaction commit 提升效能"""
        if not items:
            return True
        db = self.db if self._external_db else SessionLocal()
        try:
            history_objs = []
            for item in items:
                rec_at = item.get("recorded_at") or item.get("timestamp")
                if isinstance(rec_at, (int, float)):
                    rec_at = datetime.fromtimestamp(rec_at)
                elif not isinstance(rec_at, datetime):
                    rec_at = datetime.utcnow()

                obj = SensorHistory(
                    carId=item.get("car_id", 0),
                    carVin=item.get("car_vin"),
                    carNo=item.get("car_no"),
                    endPos=item.get("end_pos"),
                    sensorCode=item.get("sensor_code", ""),
                    sensorValue=float(item.get("sensor_value", 0.0)),
                    recordedAt=rec_at,
                    sensorName=item.get("sensor_name"),
                    sensorUnit=item.get("sensor_unit"),
                    equipmentName=item.get("equipment_name")
                )
                history_objs.append(obj)

            db.add_all(history_objs)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding batch sensor history: {e}")
            return False
        finally:
            if not self._external_db:
                db.close()

sensor_history_repo = SensorHistoryRepository()
