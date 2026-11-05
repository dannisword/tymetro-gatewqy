from datetime import datetime, timedelta
from sqlalchemy import text
from app.models.equipment_event_model import EquipmentEvent
from app.database.session import SessionLocal
from app.core.logger import logger


class EquipmentEventRepository:
    def delete_records_older_than(self, days: int) -> int:
        """刪除超過指定天數的設備事件紀錄 (equipment_events)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        db = SessionLocal()
        try:
            num_deleted = db.query(EquipmentEvent).filter(EquipmentEvent.triggeredAt < cutoff_date).delete(synchronize_session=False)
            db.commit()
            if num_deleted > 0:
                logger.info(f"[EquipmentEventRepository] Cleaned up {num_deleted} expired equipment events older than {days} days.")
                db.execute(text("PRAGMA optimize;"))
            return num_deleted
        except Exception as e:
            db.rollback()
            logger.error(f"[EquipmentEventRepository] Error cleaning up expired equipment events: {e}")
            return 0
        finally:
            db.close()

equipment_event_repo = EquipmentEventRepository()
