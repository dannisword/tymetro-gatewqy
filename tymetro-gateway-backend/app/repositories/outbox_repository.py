import time
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.outbox_model import Outbox
from app.database.session import SessionLocal
from app.core.logger import logger

class OutboxRepository(BaseRepository[Outbox]):
    """Outbox 離線暫存與重傳佇列 Repository (純 ORM 實現，無原生 SQL)"""
    def __init__(self, db: Optional[Session] = None, max_capacity: int = 10000):
        self._external_db = db is not None
        session = db or SessionLocal()
        super().__init__(Outbox, session)
        self.max_capacity = max_capacity

    def push(self, data: Dict[str, Any]) -> bool:
        """寫入補傳訊息到 Outbox (Store)，若超過容量上限自動刪除最舊資料 (FIFO)"""
        db = self.db if self._external_db else SessionLocal()
        try:
            # 1. 檢查容量限制，防止硬碟撐爆 (純 ORM)
            current_count = db.query(Outbox).count()
            if current_count >= self.max_capacity:
                overflow = (current_count - self.max_capacity) + 1
                oldest_ids = [
                    item.id for item in db.query(Outbox.id).order_by(Outbox.id.asc()).limit(overflow).all()
                ]
                if oldest_ids:
                    db.query(Outbox).filter(Outbox.id.in_(oldest_ids)).delete(synchronize_session=False)

            # 2. 新增 Outbox 記錄 (純 ORM)
            outbox_obj = Outbox(
                payload=json.dumps(data),
                createdAt=time.time(),
                retryCount=0
            )
            db.add(outbox_obj)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error pushing data to outbox: {e}")
            return False
        finally:
            if not self._external_db:
                db.close()

    def push_batch(self, items: List[Dict[str, Any]]) -> bool:
        """寫入批量補傳訊息到 Outbox，一次 DB commit 提升效能與保護硬碟壽命"""
        if not items:
            return True
        db = self.db if self._external_db else SessionLocal()
        try:
            current_count = db.query(Outbox).count()
            if current_count + len(items) > self.max_capacity:
                overflow = (current_count + len(items)) - self.max_capacity
                oldest_ids = [
                    item.id for item in db.query(Outbox.id).order_by(Outbox.id.asc()).limit(overflow).all()
                ]
                if oldest_ids:
                    db.query(Outbox).filter(Outbox.id.in_(oldest_ids)).delete(synchronize_session=False)

            outbox_objs = [
                Outbox(
                    payload=json.dumps(data),
                    createdAt=time.time(),
                    retryCount=0
                )
                for data in items
            ]
            db.add_all(outbox_objs)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error pushing batch data to outbox: {e}")
            return False
        finally:
            if not self._external_db:
                db.close()

    def fetch_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        """讀取暫存訊息準備補傳 (Forward) (純 ORM)"""
        db = self.db if self._external_db else SessionLocal()
        try:
            rows = db.query(Outbox).order_by(Outbox.id.asc()).limit(limit).all()
            results = []
            for row in rows:
                results.append({
                    "id": row.id,
                    "payload": json.loads(row.payload),
                    "retry_count": row.retryCount
                })
            return results
        except Exception as e:
            logger.error(f"Error fetching batch from outbox: {e}")
            return []
        finally:
            if not self._external_db:
                db.close()

    def delete_batch(self, ids: List[int]) -> bool:
        """成功補傳後批次刪除 (純 ORM)"""
        if not ids:
            return True
        db = self.db if self._external_db else SessionLocal()
        try:
            db.query(Outbox).filter(Outbox.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting batch from outbox: {e}")
            return False
        finally:
            if not self._external_db:
                db.close()

outbox_repo = OutboxRepository()
