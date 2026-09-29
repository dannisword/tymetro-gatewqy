import os
import shutil
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.logger import logger
from app.core.config import settings
from app.services.equipment_manager import equipment_manager
from app.repositories.sensor_history_repository import sensor_history_repo

class SchedulerService:
    """
    APScheduler 背景定期排程服務:
    - 每 1 分鐘：檢查 8 台 PFC200 設備心跳與在線狀態
    - 每日 03:00：自動備份 SQLite gateway.db 資料庫
    - 每日 03:10：自動清理 10 天前的舊日誌檔案
    - 每日 03:20：自動清理過期感測器歷史資料 (防止 SQLite 膨脹)
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

        # Job 3: 每日 03:10 執行舊日誌檔案自動清理
        self.scheduler.add_job(
            self.job_cleanup_old_logs,
            'cron',
            hour=3,
            minute=10,
            id='cleanup_old_logs',
            replace_existing=True
        )

        # Job 4: 每日 03:20 執行過期感測器歷史資料清理
        self.scheduler.add_job(
            self.job_cleanup_old_sensor_histories,
            'cron',
            hour=3,
            minute=20,
            id='cleanup_old_sensor_histories',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("[SchedulerService] APScheduler started successfully with Heartbeat Check, Daily Backup, Log Cleanup & Sensor History Retention Jobs.")

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
        """SQLite DB 每日 03:00 自動備份 Job (非同步複製 + 依 BACKUP_RETENTION_DAYS 自動清理舊備份)"""
        try:
            db_path = settings.SQLITE_DB_PATH
            backup_dir = "data/backups"
            os.makedirs(backup_dir, exist_ok=True)

            if os.path.exists(db_path):
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"gateway_backup_{date_str}.db")
                
                # 1. 使用 run_in_executor 執行同步的複製操作，防止卡死主 Event Loop
                import asyncio
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, shutil.copy2, db_path, backup_file)
                logger.info(f"[SchedulerService] Database daily backup completed: {backup_file}")

                # 2. 自動清除舊備份：依 BACKUP_RETENTION_DAYS 僅保留最新的 N 個備份檔
                backup_files = [
                    os.path.join(backup_dir, f)
                    for f in os.listdir(backup_dir)
                    if f.startswith("gateway_backup_") and f.endswith(".db")
                ]
                # 依檔名排序 (排序後舊的在前、新的在後)
                backup_files.sort()
                
                retention_days = max(1, settings.BACKUP_RETENTION_DAYS)
                if len(backup_files) > retention_days:
                    files_to_delete = backup_files[:-retention_days]
                    for f_path in files_to_delete:
                        try:
                            os.remove(f_path)
                            logger.info(f"[SchedulerService] Deleted expired database backup: {f_path}")
                        except Exception as clean_err:
                            logger.error(f"[SchedulerService] Failed to delete expired backup {f_path}: {clean_err}")
            else:
                logger.warning(f"[SchedulerService] Database file {db_path} not found for backup.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error backing up database: {e}")

    async def job_cleanup_old_logs(self):
        """每日自動清理 10 天前的舊日誌檔案 (包含舊動態格式與滾動壓縮檔)"""
        try:
            log_path_env = os.getenv("LOG_PATH", "logs/gateway.log")
            log_dir = os.path.dirname(log_path_env) or "logs"
            
            if not os.path.exists(log_dir):
                logger.warning(f"[SchedulerService] Log directory {log_dir} does not exist.")
                return

            now = datetime.now()
            limit_days = 10
            cleaned_count = 0

            for file_name in os.listdir(log_dir):
                # 匹配所有以 gateway 開頭且為 .log 或 .zip 的檔案
                if file_name.startswith("gateway") and (file_name.endswith(".log") or file_name.endswith(".zip")):
                    file_path = os.path.join(log_dir, file_name)
                    # 取得最後修改時間
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    # 判斷是否超過限期
                    if (now - mtime).days >= limit_days:
                        try:
                            os.remove(file_path)
                            logger.info(f"[SchedulerService] Deleted expired log file: {file_path}")
                            cleaned_count += 1
                        except Exception as file_err:
                            logger.error(f"[SchedulerService] Failed to delete expired log file {file_path}: {file_err}")
            
            if cleaned_count > 0:
                logger.info(f"[SchedulerService] Log cleanup completed. Deleted {cleaned_count} files.")
            else:
                logger.debug("[SchedulerService] Log cleanup: No expired log files found.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error cleaning up logs: {e}")

    async def job_cleanup_old_sensor_histories(self):
        """每日自動清理過期的感測器歷史紀錄 (以 SENSOR_HISTORY_RETENTION_DAYS 為基準，預設 30 天)"""
        try:
            import asyncio
            retention_days = settings.SENSOR_HISTORY_RETENTION_DAYS
            loop = asyncio.get_running_loop()
            deleted = await loop.run_in_executor(
                None, 
                sensor_history_repo.delete_records_older_than, 
                retention_days
            )
            if deleted > 0:
                logger.info(f"[SchedulerService] Expired sensor history cleanup completed: {deleted} records removed.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error during expired sensor history cleanup: {e}")

scheduler_service = SchedulerService()
