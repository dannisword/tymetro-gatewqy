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

        # 開機/啟動時非同步檢查（若今日 03:00 尚未開機執行備份，自動補備份並清理過期檔）
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            loop.create_task(self.check_and_run_startup_backup())
        except RuntimeError:
            pass

    def stop(self):
        """停止排程器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[SchedulerService] APScheduler stopped.")

    def _get_backup_dir(self) -> str:
        """取得備份存放目錄"""
        db_dir = os.path.dirname(settings.SQLITE_DB_PATH)
        return os.path.join(db_dir, "data/backups") if db_dir else "data/backups"

    @staticmethod
    def _perform_sqlite_backup(src_path: str, dest_path: str):
        """執行 SQLite 安全備份 (優先使用 sqlite3.Connection.backup 確保 WAL 一致性，失敗時降級為 shutil.copy2)"""
        try:
            import sqlite3
            with sqlite3.connect(src_path) as src, sqlite3.connect(dest_path) as dest:
                src.backup(dest)
        except Exception as e:
            logger.warning(f"[SchedulerService] sqlite3.backup failed ({e}), falling back to shutil.copy2")
            shutil.copy2(src_path, dest_path)

    def _cleanup_expired_backups(self, backup_dir: str):
        """依 BACKUP_RETENTION_DAYS 僅保留最新的 N 個備份檔"""
        try:
            if not os.path.exists(backup_dir):
                return
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
        except Exception as e:
            logger.error(f"[SchedulerService] Error cleaning up expired backups: {e}")

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
        """SQLite DB 每日自動備份 Job (非同步安全備份 + 依 BACKUP_RETENTION_DAYS 自動清理舊備份)"""
        try:
            db_path = settings.SQLITE_DB_PATH
            backup_dir = self._get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)

            if os.path.exists(db_path):
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"gateway_backup_{date_str}.db")
                
                # 1. 使用 run_in_executor 執行非同步備份，支援 WAL 模式安全備份
                import asyncio
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._perform_sqlite_backup, db_path, backup_file)
                logger.info(f"[SchedulerService] Database daily backup completed: {backup_file}")

                # 2. 自動清除舊備份：依 BACKUP_RETENTION_DAYS 僅保留最新的 N 個備份檔
                self._cleanup_expired_backups(backup_dir)
            else:
                logger.warning(f"[SchedulerService] Database file {db_path} not found for backup.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error backing up database: {e}")

    async def check_and_run_startup_backup(self):
        """
        開機/啟動時檢查：
        若今日 03:00 期間設備處於關機狀態而未執行資料庫備份，
        則於開機後自動補行備份與舊檔案清理。
        """
        try:
            # 稍候 3 秒，讓系統核心服務 (DB, SQLite Writer) 完成就緒
            import asyncio
            await asyncio.sleep(5)

            backup_dir = self._get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)

            now = datetime.now()
            today_prefix = now.strftime("%Y%m%d")

            # 搜尋現有備份檔 (檔名格式: gateway_backup_YYYYMMDD_HHMMSS.db)
            backup_files = [
                f for f in os.listdir(backup_dir)
                if f.startswith("gateway_backup_") and f.endswith(".db")
            ]
            backup_files.sort()

            # 檢查今日是否已存在備份檔
            today_backups = [f for f in backup_files if f.startswith(f"gateway_backup_{today_prefix}")]

            should_backup = False
            reason = ""

            if not today_backups:
                # 今日尚未產生過備份
                if now.hour >= 3:
                    should_backup = True
                    reason = f"今日已過 03:00 且無今日備份檔 (可能因關機未執行)，觸發開機補備份"
                else:
                    # 尚未到今日 03:00，檢查是否有歷史備份或是否已超過 24 小時未備份
                    if not backup_files:
                        should_backup = True
                        reason = "系統尚無任何歷史備份檔，執行首次開機備份"
                    else:
                        latest_file = backup_files[-1]
                        latest_path = os.path.join(backup_dir, latest_file)
                        mtime = datetime.fromtimestamp(os.path.getmtime(latest_path))
                        if (now - mtime).total_seconds() > 86400:
                            should_backup = True
                            reason = f"最新備份 ({latest_file}) 已超過 24 小時，執行開機補備份"

            if should_backup:
                logger.info(f"[SchedulerService] 開機備份檢查: {reason}。")
                await self.job_backup_database()
            else:
                if today_backups:
                    logger.info(f"[SchedulerService] 開機備份檢查: 今日已有備份檔 ({today_backups[-1]})，略過補備份。")
                else:
                    logger.info("[SchedulerService] 開機備份檢查: 目前時間尚未到 03:00，且最近 24 小時內已有備份，維持待 03:00 排程執行。")
                
                # 清理可能過期的舊備份
                self._cleanup_expired_backups(backup_dir)

            # 開機時同步執行日誌與過期感測歷史清理 (防止夜間關機錯過 03:10 / 03:20 排程)
            await self.job_cleanup_old_logs()
            await self.job_cleanup_old_sensor_histories()

        except Exception as e:
            logger.error(f"[SchedulerService] Error in check_and_run_startup_backup: {e}")

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
