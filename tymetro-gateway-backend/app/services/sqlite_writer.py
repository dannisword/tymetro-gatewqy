import asyncio
import time
from typing import Dict, Any, List, Optional
from app.core.logger import logger
from app.repositories.sensor_history_repository import sensor_history_repo
from app.repositories.outbox_repository import outbox_repo

class SQLiteWriter:
    """
    SQLite 獨立批次寫入器 (SQLite Batch Writer):
    - 使用 asyncio.Queue 做為記憶體暫存區 (Queue Manager)
    - 以條件觸發：當累積滿 100 筆 或 時間滿 5 秒 時自動寫入
    - 使用單一 Transaction commit 寫入 SensorHistory & Outbox
    - 大幅降低 eMMC Flash / SSD 的寫入擦擦次數，延長硬體壽命
    """
    def __init__(self, batch_size: int = 100, flush_interval_sec: float = 5.0):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def start(self):
        """啟動非同步 Queue 消費者任務"""
        self._running = True
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        logger.info(f"[SQLiteWriter] Batch Writer started (batch_size={self.batch_size}, interval={self.flush_interval_sec}s).")

    async def stop(self):
        """優雅關閉並清空剩餘 Queue 寫入 SQLite"""
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        await self.flush_remaining()
        logger.info("[SQLiteWriter] Batch Writer stopped cleanly.")

    async def push(self, item: Dict[str, Any]):
        """將單筆或遙測數據物件推入 Queue 佇列"""
        await self.queue.put(item)

    async def push_many(self, items: List[Dict[str, Any]]):
        """將多筆遙測數據物件推入 Queue 佇列"""
        for item in items:
            await self.queue.put(item)

    async def _consumer_loop(self):
        """背景消費輪詢：當 Queue 累積滿 batch_size 或超過 5 秒時觸發批量寫入"""
        items: List[Dict[str, Any]] = []
        last_flush_time = time.time()

        while self._running:
            try:
                # 計算距離上次刷庫的時間差
                time_since_last_flush = time.time() - last_flush_time
                timeout = max(0.1, self.flush_interval_sec - time_since_last_flush)

                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                    items.append(item)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    pass

                now = time.time()
                # 滿足 100 筆 或 超過 5 秒觸發批量寫入
                if len(items) >= self.batch_size or (items and (now - last_flush_time) >= self.flush_interval_sec):
                    await self._write_batch(items)
                    items.clear()
                    last_flush_time = now

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SQLiteWriter] Exception in consumer loop: {e}")

        # 若 Cancelled 退出，清空剩餘 items
        if items:
            await self._write_batch(items)

    async def _write_batch(self, items: List[Dict[str, Any]]):
        """實際呼叫 Repository 執行 ORM 批量寫入"""
        if not items:
            return
        try:
            # 異步線程中執行資料庫 commit 寫入
            loop = asyncio.get_running_loop()
            
            # 1. 寫入 SensorHistory
            h_success = await loop.run_in_executor(None, sensor_history_repo.add_batch, items)
            # 2. 寫入 Outbox (離線補傳佇列)
            o_success = await loop.run_in_executor(None, outbox_repo.push_batch, items)

            if h_success and o_success:
                logger.info(f"[SQLiteWriter] Executemany Success: Flushed {len(items)} telemetry records into SQLite.")
            else:
                logger.error(f"[SQLiteWriter] Failed to write batch of {len(items)} items to SQLite.")
        except Exception as e:
            logger.error(f"[SQLiteWriter] Error during _write_batch: {e}")

    async def flush_remaining(self):
        """關閉時刷新剩餘佇列資料"""
        remaining_items: List[Dict[str, Any]] = []
        while not self.queue.empty():
            try:
                remaining_items.append(self.queue.get_nowait())
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        if remaining_items:
            logger.info(f"[SQLiteWriter] Flushing remaining {len(remaining_items)} queue items on shutdown...")
            await self._write_batch(remaining_items)

sqlite_writer = SQLiteWriter()
