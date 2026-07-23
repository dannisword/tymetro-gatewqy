import time
import json
import sqlite3
from typing import List, Dict, Any, Optional
from app.core.config_yaml import yaml_settings
from app.core.logger import logger

def init_outbox_table():
    """初始化 SQLite WAL 模式與 outbox 暫存資料表"""
    db_path = yaml_settings.database.db_path
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 開啟 WAL 模式提升併發寫入效能與壽命
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                retry_count INTEGER DEFAULT 0
            );
        """)
        conn.commit()
        conn.close()
        logger.info(f"Outbox table initialized in {db_path} with WAL mode.")
    except Exception as e:
        logger.error(f"Failed to initialize outbox table: {e}")

class OutboxRepository:
    def __init__(self, db_path: Optional[str] = None, max_capacity: int = 10000):
        self.db_path = db_path or yaml_settings.database.db_path
        self.max_capacity = max_capacity

    def push(self, data: Dict[str, Any]) -> bool:
        """寫入補傳訊息到 Outbox (Store)，若超過容量上限自動刪除最舊資料 (FIFO)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 檢查容量限制，防止硬碟撐爆
            cursor.execute("SELECT COUNT(*) FROM outbox")
            current_count = cursor.fetchone()[0]
            if current_count >= self.max_capacity:
                overflow = (current_count - self.max_capacity) + 1
                cursor.execute(
                    "DELETE FROM outbox WHERE id IN (SELECT id FROM outbox ORDER BY id ASC LIMIT ?)",
                    (overflow,)
                )

            cursor.execute(
                "INSERT INTO outbox (payload, created_at, retry_count) VALUES (?, ?, 0)",
                (json.dumps(data), time.time())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error pushing data to outbox: {e}")
            return False


    def fetch_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        """讀取暫存訊息準備補傳 (Forward)"""
        results = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, payload, retry_count FROM outbox ORDER BY id ASC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    "id": row[0],
                    "payload": json.loads(row[1]),
                    "retry_count": row[2]
                })
            conn.close()
        except Exception as e:
            logger.error(f"Error fetching batch from outbox: {e}")
        return results

    def delete_batch(self, ids: List[int]) -> bool:
        """成功補傳後批次刪除」"""
        if not ids:
            return True
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(f"DELETE FROM outbox WHERE id IN ({placeholders})", ids)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting batch from outbox: {e}")
            return False

outbox_repo = OutboxRepository()
