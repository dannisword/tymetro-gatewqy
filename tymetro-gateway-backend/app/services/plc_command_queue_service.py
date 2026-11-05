"""
PLC 設定指令重試佇列 worker
==========================
execute_batch 首輪未確認的端點會寫入 plc_command_tasks (PENDING)，
本 worker 週期性取出 PENDING 任務，依 (指令, 設定值, 車組, events) 分組重新下發並等待確認，
直到成功或任務建立滿 PLC_QUEUE_MAX_AGE_SEC (10 分鐘) 為止 (重啟後仍會繼續，因為存在資料表)。
"""

import asyncio
from collections import defaultdict
from typing import Optional

from app.core.logger import logger
from app.database.session import SessionLocal
from app.models.plc_command_task_model import PlcCommandTask
from app.services.plc_command_service import PLC_QUEUE_MAX_ATTEMPTS, PlcCommandError, PlcCommandService
from app.utils.datetime_util import get_local_now

# 每輪重試之間的間隔 (不含每輪最長 10 秒的確認等待)
PLC_QUEUE_INTERVAL_SEC = 60
# 自任務建立起最多重試 10 分鐘，逾時放棄
PLC_QUEUE_MAX_AGE_SEC = 600
# 任務有時效性：建立超過 1 小時 (如服務停機後才重啟) 一律不再執行，直接標為 EXPIRED
PLC_QUEUE_STALE_SEC = 3600
PLC_QUEUE_STARTUP_DELAY_SEC = 15


class PlcCommandQueueWorker:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
            logger.info("[PlcQueue] Retry worker started.")

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None

    async def _run(self):
        await asyncio.sleep(PLC_QUEUE_STARTUP_DELAY_SEC)
        while True:
            try:
                await self.process_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[PlcQueue] 處理佇列失敗: {e}")
            await asyncio.sleep(PLC_QUEUE_INTERVAL_SEC)

    async def process_once(self) -> None:
        db = SessionLocal()
        try:
            rows = (
                db.query(PlcCommandTask)
                .filter(PlcCommandTask.status == "PENDING")
                .order_by(PlcCommandTask.id)
                .all()
            )
            now = get_local_now()
            groups = defaultdict(list)
            stale = []
            for r in rows:
                if r.createdAt and (now - r.createdAt).total_seconds() >= PLC_QUEUE_STALE_SEC:
                    stale.append(r)
                    continue
                groups[(r.command, r.value, r.trainCode, r.event)].append(r.id)

            if stale:
                service = PlcCommandService(db)
                for r in stale:
                    text = f"任務已超過 {PLC_QUEUE_STALE_SEC // 60} 分鐘，不再執行"
                    r.status = "EXPIRED"
                    r.lastError = text
                    r.updatedAt = now
                    logger.warning(f"[PlcQueue] {r.command} {r.carNo}-{r.endPos}端 {text}")
                    self._finish_log(service, r, "FAILED", text)
                db.commit()

            for (command, value, train_code, event), ids in groups.items():
                await self._retry_group(db, command, value, train_code, event, ids)
        finally:
            db.close()

    async def _retry_group(self, db, command, value, train_code, event, ids) -> None:
        tasks = db.query(PlcCommandTask).filter(PlcCommandTask.id.in_(ids)).order_by(PlcCommandTask.id).all()
        tasks = [t for t in tasks if t.status == "PENDING"]
        if not tasks:
            return
        targets = [{"carNo": t.carNo, "endPos": t.endPos} for t in tasks]
        service = PlcCommandService(db)
        results = None
        error: Optional[str] = None
        fatal = False
        try:
            results = await service.execute_batch(
                command=command, value=value, targets=targets, operator="plc_queue",
                ip_address=None, train_code=train_code, event=event,
                enqueue_failed=False, record=False,
            )
        except PlcCommandError as e:
            # 指令不支援 / 設定值不合法 / 找不到任何設備：重試也不會成功
            error, fatal = str(e), True
        except asyncio.CancelledError:
            raise
        except Exception as e:
            error = f"重試例外: {e}"
            logger.error(f"[PlcQueue] {command} 重試例外: {e}")

        # 重新讀取：期間可能被新指令取代 (SUPERSEDED)，只更新仍為 PENDING 者
        db.expire_all()
        now = get_local_now()
        by_key = {}
        if results is not None and len(results) == len(tasks):
            by_key = {t.id: r for t, r in zip(tasks, results)}

        for task in db.query(PlcCommandTask).filter(PlcCommandTask.id.in_(ids)).all():
            if task.status != "PENDING":
                continue
            result = by_key.get(task.id)
            task.attemptCount = int(task.attemptCount or 0) + 1
            task.updatedAt = now
            label = f"{task.carNo}-{task.endPos}端"
            if result is not None and result.ok:
                task.status = "SUCCESS"
                task.lastError = None
                self._finish_log(service, task, "SUCCESS", f"佇列第 {task.attemptCount} 次重試成功 ({result.message})")
                logger.info(f"[PlcQueue] {command} {label} 第 {task.attemptCount} 次重試成功")
                continue
            reason = error or (result.error or result.message if result is not None else None) or "未確認"
            task.lastError = reason[:500]
            age = (now - task.createdAt).total_seconds() if task.createdAt else 0
            # 下一輪會落在期限之後即視為最後一次，不再多等一輪
            expired = age + PLC_QUEUE_INTERVAL_SEC >= PLC_QUEUE_MAX_AGE_SEC
            if fatal or expired or task.attemptCount >= int(task.maxAttempts or PLC_QUEUE_MAX_ATTEMPTS):
                task.status = "FAILED"
                self._finish_log(service, task, "FAILED", f"重試 {task.attemptCount} 次 ({int(age)} 秒) 仍未完成: {reason}")
                logger.warning(f"[PlcQueue] {command} {label} 放棄 (已重試 {task.attemptCount} 次): {reason}")
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[PlcQueue] 更新佇列狀態失敗: {e}")

    @staticmethod
    def _finish_log(service: PlcCommandService, task: PlcCommandTask, status: str, text: str) -> None:
        """佇列最終結果 (成功 / 放棄) 才補寫一筆設定紀錄，避免每輪重試都產生紀錄"""
        service._write_setting_log(
            str(task.command), str(task.operator or "plc_queue"),
            f"{task.carNo}-{task.endPos}端 值={task.value:g} | {text}" if task.value is not None else f"{task.carNo}-{task.endPos}端 | {text}",
            "", {}, status=status, error_message=text if status == "FAILED" else None,
        )


plc_command_queue_worker = PlcCommandQueueWorker()
