from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.setting_log_model import SettingLog
from app.repositories.base_repository import BaseRepository
from app.database.session import SessionLocal
from app.core.logger import logger

class SettingLogRepository(BaseRepository[SettingLog]):
    def __init__(self, db: Optional[Session] = None):
        self._external_db = db is not None
        session = db or SessionLocal()
        super().__init__(SettingLog, session)

    def delete_records_older_than(self, days: int) -> int:
        """刪除超過指定天數的設定與審計紀錄，防止 SQLite 檔案過度膨脹"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        db = self.db if self._external_db else SessionLocal()
        try:
            num_deleted = db.query(SettingLog).filter(SettingLog.recordedAt < cutoff_date).delete(synchronize_session=False)
            db.commit()
            if num_deleted > 0:
                logger.info(f"[SettingLogRepository] Cleaned up {num_deleted} expired setting/audit log records older than {days} days.")
                db.execute(text("PRAGMA optimize;"))
            return num_deleted
        except Exception as e:
            db.rollback()
            logger.error(f"[SettingLogRepository] Error cleaning up expired setting logs: {e}")
            return 0
        finally:
            if not self._external_db:
                db.close()

setting_log_repo = SettingLogRepository()
