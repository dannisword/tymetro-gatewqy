import os
from typing import cast
import shutil
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.logger import logger
from app.core.config import settings
from app.services.equipment_manager import equipment_manager
from app.repositories.sensor_history_repository import sensor_history_repo
from app.repositories.setting_log_repository import setting_log_repo
from app.repositories.equipment_event_repository import equipment_event_repo
from app.repositories.plc_command_task_repository import plc_command_task_repo

class SchedulerService:
    """
    APScheduler 背景定期排程服務:
    - 每 1 分鐘：檢查 8 台 PFC200 設備心跳與在線狀態
    - 每日 03:00：自動備份 SQLite gateway.db 資料庫
    - 每日 03:10：自動清理 10 天前的舊日誌檔案
    - 每日 03:20：自動清理過期感測器歷史資料 (防止 SQLite 膨脹)
    - 每日 03:30：自動清理過期設定與審計紀錄 (setting_logs)
    - 每日 03:40：自動清理過期設備事件紀錄 (equipment_events)
    - 每日 03:50：自動清理過期 PLC 重試佇列紀錄 (plc_command_tasks，保留 7 天)
    - 每小時第 10 分鐘：批次上傳離線感測器歷史資料
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
        if settings.BACKUP_ENABLED:
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

        # Job 5: 每日 03:30 執行過期設定與審計紀錄清理 (setting_logs)
        self.scheduler.add_job(
            self.job_cleanup_old_setting_logs,
            'cron',
            hour=3,
            minute=30,
            id='cleanup_old_setting_logs',
            replace_existing=True
        )

        # Job 5b: 每日 03:40 執行過期設備事件紀錄清理 (equipment_events)
        self.scheduler.add_job(
            self.job_cleanup_old_equipment_events,
            'cron',
            hour=3,
            minute=40,
            id='cleanup_old_equipment_events',
            replace_existing=True
        )

        # Job 5c: 每日 03:50 執行過期 PLC 重試佇列紀錄清理 (plc_command_tasks)
        self.scheduler.add_job(
            self.job_cleanup_old_plc_command_tasks,
            'cron',
            hour=3,
            minute=50,
            id='cleanup_old_plc_command_tasks',
            replace_existing=True
        )

        # Job 6: 每小時第 10 分鐘上傳離線期間累積的感測器歷史資料到後端 (例如: 01:10, 02:10...)
        self.scheduler.add_job(
            self.job_upload_offline_sensor_histories,
            'cron',
            minute=10,
            id='upload_offline_sensor_histories',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("[SchedulerService] APScheduler started successfully with Heartbeat Check, Daily Backup, Log Cleanup, Retention & Offline Upload Jobs.")

        # 開機/啟動時非同步檢查（若今日 03:00 尚未開機執行備份，自動補備份並清理過期檔）
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            if settings.BACKUP_ENABLED:
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
        """刪除早於 BACKUP_RETENTION_DAYS 天前的備份檔 (依檔名日期判斷，且至少保留最新一份)"""
        try:
            if not os.path.exists(backup_dir):
                return
            backup_files = sorted(
                f for f in os.listdir(backup_dir)
                if f.startswith("gateway_backup_") and f.endswith(".db")
            )
            if len(backup_files) <= 1:
                return

            retention_days = max(1, settings.BACKUP_RETENTION_DAYS)
            cutoff = (datetime.now() - timedelta(days=retention_days)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            logger.debug(f"[SchedulerService] retention_days: {retention_days}")
            # 最新一份永遠保留，避免長時間關機後開機時備份被全數清空
            for f_name in backup_files[:-1]:
                f_path = os.path.join(backup_dir, f_name)
                try:
                    # 檔名格式: gateway_backup_YYYYMMDD_HHMMSS.db
                    file_date = datetime.strptime(f_name[len("gateway_backup_"):][:8], "%Y%m%d")
                except ValueError:
                    continue
                if file_date < cutoff:
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

            # 開機時同步執行日誌、過期感測歷史與設定/審計日誌清理 (防止夜間關機錯過 03:10 / 03:20 / 03:30 排程)
            await self.job_cleanup_old_logs()
            await self.job_cleanup_old_sensor_histories()
            await self.job_cleanup_old_setting_logs()
            await self.job_cleanup_old_equipment_events()
            await self.job_cleanup_old_plc_command_tasks()

        except Exception as e:
            logger.error(f"[SchedulerService] Error in check_and_run_startup_backup: {e}")

    async def job_cleanup_old_logs(self):
        """每日自動清理過期的舊日誌檔案 (依 LOG_RETENTION_DAYS 天數，包含舊動態格式與滾動壓縮檔)"""
        try:
            log_path_env = settings.LOG_PATH or os.getenv("LOG_PATH", "logs/gateway.log")
            log_dir = os.path.dirname(log_path_env) or "logs"
            
            if not os.path.exists(log_dir):
                logger.warning(f"[SchedulerService] Log directory {log_dir} does not exist.")
                return

            now = datetime.now()
            limit_days = max(1, settings.LOG_RETENTION_DAYS)
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
        """每日自動清理過期的感測器歷史紀錄 (以 SENSOR_HISTORY_RETENTION_DAYS 為基準，預設 60 天)"""
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

    async def job_cleanup_old_equipment_events(self):
        """每日自動清理過期的設備事件紀錄 (以 EQUIPMENT_EVENT_RETENTION_DAYS 為基準，預設 60 天)"""
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            deleted = await loop.run_in_executor(
                None,
                equipment_event_repo.delete_records_older_than,
                settings.EQUIPMENT_EVENT_RETENTION_DAYS
            )
            if deleted > 0:
                logger.info(f"[SchedulerService] Expired equipment events cleanup completed: {deleted} records removed.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error during expired equipment events cleanup: {e}")

    async def job_cleanup_old_plc_command_tasks(self):
        """每日自動清理過期的 PLC 重試佇列紀錄 (以 PLC_COMMAND_TASK_RETENTION_DAYS 為基準，預設 7 天)"""
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            deleted = await loop.run_in_executor(
                None,
                plc_command_task_repo.delete_records_older_than,
                settings.PLC_COMMAND_TASK_RETENTION_DAYS
            )
            if deleted > 0:
                logger.info(f"[SchedulerService] Expired plc command tasks cleanup completed: {deleted} records removed.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error during expired plc command tasks cleanup: {e}")

    async def job_cleanup_old_setting_logs(self):
        """每日自動清理過期的設定與審計紀錄 (以 SETTING_LOG_RETENTION_DAYS 為基準，預設 60 天)"""
        try:
            import asyncio
            retention_days = settings.SETTING_LOG_RETENTION_DAYS
            loop = asyncio.get_running_loop()
            deleted = await loop.run_in_executor(
                None,
                setting_log_repo.delete_records_older_than,
                retention_days
            )
            if deleted > 0:
                logger.info(f"[SchedulerService] Expired setting/audit logs cleanup completed: {deleted} records removed.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error during expired setting/audit logs cleanup: {e}")

    async def job_upload_offline_sensor_histories(self):
        """每小時將 is_offline=1 的感測器歷史批次上傳到中央後端 (POST /api/v1/sensor-histories/batch)"""
        import asyncio
        from app.services.backend_mqtt_service import backend_mqtt_service
        from app.utils.http_util import HttpUtil

        if not backend_mqtt_service.is_connected:
            logger.info("[SchedulerService] Offline history upload skipped: cloud not connected.")
            return

        loop = asyncio.get_running_loop()
        url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/sensor-histories/batch"
        batch_size = 1000  # 後端單次上限 10000
        total = 0
        try:
            for _ in range(200):  # 安全上限，避免無窮迴圈
                rows = await loop.run_in_executor(None, sensor_history_repo.fetch_offline, batch_size)
                if not rows:
                    break
                token = await loop.run_in_executor(None, HttpUtil.get_central_backend_token)
                if not token:
                    logger.warning("[SchedulerService] Offline history upload aborted: no backend token.")
                    break
                records = [{
                    "carVin": r.carVin,
                    "carNo": r.carNo,
                    "endPos": r.endPos,
                    "sensorCode": r.sensorCode,
                    "sensorValue": r.sensorValue,
                    # gateway 存 UTC naive，補上時區避免被後端當成臺灣時間
                    "recordedAt": r.recordedAt.isoformat() + "Z",
                } for r in rows if r.carVin]
                skipped_ids = [cast(int, r.id) for r in rows if not r.carVin]
                if records:
                    resp = await loop.run_in_executor(
                        None,
                        lambda: HttpUtil.post(url, data={"records": records},
                                              headers={"Authorization": f"Bearer {token}"}, timeout=30)
                    )
                    if not resp.get("success"):
                        logger.warning(f"[SchedulerService] Offline history upload failed: {resp.get('message')}")
                        break
                # 後端已回應成功 (含其略過的筆數)；無 carVin 者無法被後端接受，一併清除標記避免卡住
                ids = [cast(int, r.id) for r in rows]
                await loop.run_in_executor(None, sensor_history_repo.mark_uploaded, ids)
                total += len(records)
                if skipped_ids:
                    logger.warning(f"[SchedulerService] {len(skipped_ids)} offline records without car_vin were dropped from upload.")
                if len(rows) < batch_size:
                    break
            if total:
                logger.info(f"[SchedulerService] Offline sensor history upload completed: {total} records.")
        except Exception as e:
            logger.error(f"[SchedulerService] Error during offline sensor history upload: {e}")

scheduler_service = SchedulerService()
