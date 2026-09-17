"""
排程執行引擎 (SchedulerEngine)
=============================
專責管理 Gateway 本地的「每小時排程 (Hourly Schedule)」生命週期：
- 啟動時從資料庫載入所有 isActive=True 且 scheduleType='hourly' 的排程。
- 支援 hourly 觸發器：CronTrigger(minute=minuteOfHour)。
- 每次執行自動更新排程之 lastRunAt 與 nextRunAt。
- 提供 reload_schedule(id) 與 reload_all() 供 API 層即時同步。
- 內建每小時核心任務：SYNC_SCHEDULE_CONFIG (定期依時段矩陣同步溫度設定)。
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Callable, cast

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from app.core.logger import logger
from app.database.session import SessionLocal
from app.models.schedule_model import Schedule
from app.models.config_model import Config
from app.models.sensor_model import Sensor
from app.models.setting_log_model import SettingLog
from app.services.audit_log_service import AuditLogService
from app.utils.datetime_util import get_active_season_by_date, get_local_now, LOCAL_TZ


class SchedulerEngine:
    """APScheduler 每小時排程執行引擎"""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._job_prefix = "sched_"
        self.task_registry: Dict[str, Callable] = {
            "SYNC_SCHEDULE_CONFIG": self._task_sync_schedule_config
        }
        logger.info("[SchedulerEngine] Initialized for hourly schedule handling.")

    # ──────────────────────────────────────────────
    # 生命週期
    # ──────────────────────────────────────────────

    def start(self):
        """在應用程式啟動 (lifespan) 時呼叫"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        self._scheduler = AsyncIOScheduler(event_loop=loop, timezone=LOCAL_TZ)
        self.reload_all()
        self._scheduler.start()
        logger.info("[SchedulerEngine] APScheduler started successfully.")

    def shutdown(self):
        """在應用程式關閉時安全停止"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("[SchedulerEngine] APScheduler shut down.")

    # ──────────────────────────────────────────────
    # 排程重載與管理
    # ──────────────────────────────────────────────

    def reload_schedule(self, schedule_id: Any):
        """新增 / 修改 / 刪除後即時重新同步單一排程"""
        if not self._scheduler:
            logger.warning("[SchedulerEngine] Scheduler not started yet. Skipping reload.")
            return

        schedule_id = int(schedule_id)
        job_id = self._job_id(schedule_id)
        self._remove_job_if_exists(job_id)


        db = SessionLocal()
        try:
            row: Optional[Schedule] = db.query(Schedule).get(schedule_id)
            if row and row.isActive:
                # 僅處理每小時排程 (hourly)
                stype = (row.scheduleType or "").strip().lower()
                if stype == "hourly":
                    self._add_job(row)
                    logger.info(f"[SchedulerEngine] Reloaded hourly schedule [{row.id}] '{row.name}'.")
                else:
                    logger.info(f"[SchedulerEngine] Schedule [{row.id}] type '{row.scheduleType}' is not hourly, skipped.")
            else:
                logger.info(f"[SchedulerEngine] Schedule [{schedule_id}] disabled or deleted — job removed.")
        except Exception as e:
            logger.error(f"[SchedulerEngine] Failed to reload schedule [{schedule_id}]: {e}")
        finally:
            db.close()

    def reload_all(self):
        """完整載入/重新整理資料庫中所有啟用的每小時排程"""
        if not self._scheduler:
            return

        # 移除所有由本引擎管理的 job
        for job in self._scheduler.get_jobs():
            if job.id.startswith(self._job_prefix):
                job.remove()

        db = SessionLocal()
        try:
            # 只載入每小時排程 (hourly)
            rows = db.query(Schedule).filter(
                Schedule.isActive == True,
                Schedule.scheduleType == "hourly"
            ).all()

            for row in rows:
                self._add_job(row)
            logger.info(f"[SchedulerEngine] Loaded {len(rows)} active hourly schedule(s) from DB.")
        except Exception as e:
            logger.error(f"[SchedulerEngine] Failed to load hourly schedules from DB: {e}")
        finally:
            db.close()

    def _job_id(self, schedule_id: int) -> str:
        return f"{self._job_prefix}{schedule_id}"

    def _add_job(self, row: Schedule):
        """依 hourly 設定建立 trigger 並加入排程器"""
        if not self._scheduler:
            return

        schedule_id = cast(int, row.id)
        job_id = self._job_id(schedule_id)
        trigger = self._build_trigger(row)
        if trigger is None:
            logger.warning(f"[SchedulerEngine] Schedule [{schedule_id}] '{row.name}' trigger build failed — skipped.")
            return

        self._scheduler.add_job(
            func=self._execute_schedule,
            trigger=trigger,
            args=[schedule_id],
            id=job_id,
            name=row.name,
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(
            f"[SchedulerEngine] Scheduled [{schedule_id}] '{row.name}' | type={row.scheduleType} | trigger={trigger}"
        )

    def _build_trigger(self, row: Schedule) -> Optional[CronTrigger]:
        """僅針對 hourly (每小時) 建立 CronTrigger(minute=minuteOfHour)"""
        try:
            stype = (row.scheduleType or "").strip().lower()
            if stype == "hourly":
                minute = row.minuteOfHour if row.minuteOfHour is not None else 0
                return CronTrigger(minute=minute)
            else:
                logger.debug(f"[SchedulerEngine] Non-hourly type '{stype}' ignored.")
                return None
        except Exception as e:
            logger.error(f"[SchedulerEngine] Build trigger error for schedule [{row.id}]: {e}")
            return None

    def _remove_job_if_exists(self, job_id: str):
        if not self._scheduler:
            return
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

    # ──────────────────────────────────────────────
    # 排程執行回呼與任務派發
    # ──────────────────────────────────────────────

    async def _execute_schedule(self, schedule_id: int):
        """排程觸發執行時呼叫：更新執行時間並執行對應任務"""
        db = SessionLocal()
        try:
            row: Optional[Schedule] = db.query(Schedule).get(schedule_id)
            if row is None:
                logger.warning(f"[SchedulerEngine] Schedule [{schedule_id}] not found during execution.")
                return

            now = get_local_now()
            row.lastRunAt = now  # type: ignore

            if self._scheduler:
                job: Optional[Job] = self._scheduler.get_job(self._job_id(schedule_id))
                if job and job.next_run_time:
                    row.nextRunAt = job.next_run_time.replace(tzinfo=None)  # type: ignore


            db.commit()
            logger.info(
                f"[SchedulerEngine] Executed hourly schedule [{schedule_id}] '{row.name}' "
                f"at {now.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # 依 taskCode 執行對應任務
            task_code = (row.taskCode or "").strip()
            if task_code:
                handler = self.task_registry.get(task_code)
                if handler:
                    try:
                        await handler()
                    except Exception as he:
                        logger.error(f"[SchedulerEngine] Handler error for task '{task_code}': {he}")
                else:
                    logger.warning(f"[SchedulerEngine] No handler registered for taskCode '{task_code}'")
            else:
                logger.info(f"[SchedulerEngine] No taskCode specified for schedule [{schedule_id}] '{row.name}'")

        except asyncio.CancelledError:
            db.rollback()
            logger.info(f"[SchedulerEngine] Schedule [{schedule_id}] execution cancelled.")
        except Exception as e:
            db.rollback()
            logger.error(f"[SchedulerEngine] Error executing schedule [{schedule_id}]: {e}")
        finally:
            db.close()

    # ──────────────────────────────────────────────
    # 審計日誌輔助方法
    # ──────────────────────────────────────────────

    def _record_audit_log(
        self,
        db,
        status: str,
        detail: str,
        action: str = "sync_schedule_config",
        audit_category: str = "schedule",
        operator: str = "system_scheduler",
        ip_address: str = "127.0.0.1"
    ):
        """記錄排程引擎審計日誌"""
        try:
            audit_service = AuditLogService(db)
            audit_service.log(
                auditCategory=audit_category,
                action=action,
                status=status,
                operator=operator,
                ipAddress=ip_address,
                detail=detail[:1000] if detail else None
            )
        except Exception as err:
            logger.error(f"[SchedulerEngine] Failed to write audit log: {err}")

    # ──────────────────────────────────────────────
    # 每小時核心任務：SYNC_SCHEDULE_CONFIG
    # ──────────────────────────────────────────────

    async def _task_sync_schedule_config(self):
        """定期將時段排程溫度設定同步至系統設定與暫存器"""
        logger.info("[SchedulerEngine Task] Running SYNC_SCHEDULE_CONFIG (Hourly Sync)...")
        db = SessionLocal()
        try:
            now = get_local_now()

            # 1. 取得當前啟用季節模式 (從 Config 讀取 ACTIVE_SEASON_MODE，若無則依當前日期自動計算)
            active_mode_config = db.query(Config).filter(Config.configType == "ACTIVE_SEASON_MODE").first()
            active_mode = None
            if active_mode_config and active_mode_config.configContent:
                active_mode = active_mode_config.configContent.strip()

            if not active_mode:
                active_mode = get_active_season_by_date(now)

            # 2. 取得時段排程矩陣 (SCHEDULE)
            schedule_config = db.query(Config).filter(Config.configType == "SCHEDULE").first()
            if not schedule_config or not schedule_config.configContent:
                err_msg = "SCHEDULE 設定內容為空"
                logger.warning(f"[SchedulerEngine Task] SYNC_SCHEDULE_CONFIG skipped: {err_msg}.")
                self._record_audit_log(db, status="failure", detail=f"排程同步失敗: {err_msg}")
                return

            schedules_dict = json.loads(schedule_config.configContent)
            matrix = schedules_dict.get(active_mode)
            if not matrix:
                err_msg = f"找不到季節模式 '{active_mode}' 的排程矩陣"
                logger.warning(f"[SchedulerEngine Task] {err_msg}.")
                self._record_audit_log(db, status="failure", detail=f"排程同步失敗: {err_msg}")
                return

            # 3. 計算當前時間之 星期 (0-6) 與 小時 (0-23)
            hour = now.hour
            py_weekday = now.weekday()  # 0=Mon, 6=Sun
            js_weekday = (py_weekday + 1) % 7  # 0=Sun, 1=Mon, ..., 6=Sat

            if hour < 0 or hour >= len(matrix) or js_weekday < 0 or js_weekday >= len(matrix[hour]):
                err_msg = f"時段索引超出範圍: hour={hour}, weekday={js_weekday}"
                logger.error(f"[SchedulerEngine Task] {err_msg}")
                self._record_audit_log(db, status="failure", detail=f"排程同步失敗: {err_msg}")
                return

            # 4. 取得當前時段目標溫度設定值
            target_val = float(matrix[hour][js_weekday])
            logger.info(
                f"[SchedulerEngine Task] Time: {now.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Mode: {active_mode} | Day: {js_weekday} | Hour: {hour} -> Target Temp: {target_val}°C"
            )

            # 5. 更新 sensors 資料表中所有溫度設定點 (D40121)
            temp_sensors = db.query(Sensor).filter(
                Sensor.sensorType == "SETTING",
                Sensor.sensorCode == "D40121"
            ).all()

            updated_count = 0
            for s in temp_sensors:
                s.sensorValue = target_val  # type: ignore
                updated_count += 1

            # 6. 寫入一筆設定歷程紀錄 (setting_logs)
            log_entry = SettingLog(
                settingType="排程控制 (Hourly)",
                value=str(target_val),
                operator="system_scheduler",
                isNotified=False,
                topic="SCHEDULE/SYNC",
                payload=json.dumps({
                    "mode": active_mode,
                    "day": js_weekday,
                    "hour": hour,
                    "targetTemp": target_val,
                    "updatedSensors": updated_count
                }, ensure_ascii=False)
            )
            db.add(log_entry)
            db.commit()

            # 7. 寫入審計日誌 (audit_logs)
            self._record_audit_log(
                db,
                status="success",
                detail=f"排程同步成功: 季節模式={active_mode}, 星期={js_weekday}, 時={hour}, 目標溫度={target_val}°C, 更新感測器數量={updated_count}"
            )

            logger.info(f"[SchedulerEngine Task] Successfully updated {updated_count} sensor(s) to target temp {target_val}°C.")

            # 8. 若 Local MQTT 服務啟用，廣播排程設定異動通知
            try:
                from app.services.gateway_mqtt_service import gateway_mqtt_service
                notify_topic = "TYMC/AIR/SCHEDULE/ACTIVE"
                payload_str = json.dumps({
                    "timestamp": now.isoformat(),
                    "mode": active_mode,
                    "dayIndex": js_weekday,
                    "hour": hour,
                    "targetTemp": target_val
                })
                await gateway_mqtt_service.publish_message(notify_topic, payload_str)
            except Exception as mqtt_err:
                logger.debug(f"[SchedulerEngine Task] Local MQTT notify omitted or error: {mqtt_err}")

        except Exception as e:
            db.rollback()
            err_msg = str(e)
            logger.error(f"[SchedulerEngine Task] SYNC_SCHEDULE_CONFIG error: {err_msg}")
            self._record_audit_log(db, status="failure", detail=f"排程同步異常: {err_msg}")
        finally:
            db.close()


# 全域單例
scheduler_engine = SchedulerEngine()
