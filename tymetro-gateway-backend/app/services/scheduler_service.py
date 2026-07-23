import os
import shutil
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.logger import logger
from app.services.equipment_manager import equipment_manager

class SchedulerService:
    """
    APScheduler 背景定期排程服務:
    - 每 1 分鐘：檢查 8 台 PFC200 設備心跳與在線狀態
    - 每日 03:00：自動備份 SQLite gateway.db 資料庫
    """
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """設定並啟動排程器"""
        # Job 1: 每 1 分鐘檢查設備心跳在線狀態
        self.scheduler.add_job(
            self.job_check_equipment_heartbeats,
            'interval',
            seconds=60,
            id='check_equipment_heartbeats',
            replace_existing=True
        )

        # Job 2: 每日 03:00 執行 SQLite 資料庫自動備份
        self.scheduler.add_job(
            self.job_backup_database,
            'cron',
            hour=3,
            minute=0,
            id='backup_database',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("[SchedulerService] APScheduler started successfully with Heartbeat Check & Daily Backup Jobs.")

    def stop(self):
        """停止排程器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[SchedulerService] APScheduler stopped.")

    async def job_check_equipment_heartbeats(self):
        """心跳檢查 Job"""
        try:
            offline_list = equipment_manager.check_health(timeout_sec=60.0)
            if offline_list:
                logger.warning(f"[SchedulerService] Equipment Health Check: {len(offline_list)} equipments marked OFFLINE: {offline_list}")
            else:
                logger.debug("[SchedulerService] Equipment Health Check: All registered PFC equipments are ONLINE.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error in job_check_device_heartbeats: {e}")

    async def job_backup_database(self):
        """SQLite DB 每日 03:00 自動備份 Job"""
        try:
            db_path = "gateway.db"
            backup_dir = "data/backups"
            os.makedirs(backup_dir, exist_ok=True)

            if os.path.exists(db_path):
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"gateway_backup_{date_str}.db")
                shutil.copy2(db_path, backup_file)
                logger.info(f"[SchedulerService] Database daily backup completed: {backup_file}")
            else:
                logger.warning(f"[SchedulerService] Database file {db_path} not found for backup.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error backing up database: {e}")

scheduler_service = SchedulerService()
