from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.models.base import AuditModel, IdType

class Schedule(AuditModel):
    __tablename__ = "schedules"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    name = Column(String(100), nullable=False, comment="排程名稱")
    scheduleType = Column("schedule_type", String(50), nullable=False, comment="排程類型: hourly (每小時), minutely (每分鐘), fixed_time (固定時間), cycle_time (固定週期)")
    taskCode = Column("task_code", String(50), nullable=True, comment="任務代碼 (例如: SYNC_DEVICE, MONITOR_ALARM)")
    cronExpression = Column("cron_expression", String(100), nullable=True, comment="Cron 表達式 (可選)")
    minuteOfHour = Column("minute_of_hour", Integer, nullable=True, comment="每小時的第幾分鐘執行 (0-59)，適用於 hourly")
    secondOfMinute = Column("second_of_minute", Integer, nullable=True, comment="每分鐘的第幾秒執行 (0-59)，適用於 minutely")
    fixedTime = Column("fixed_time", String(50), nullable=True, comment="固定執行時間 (格式 HH:mm:ss)，適用於 fixed_time")
    cycleTime = Column("cycle_time", Integer, nullable=True, comment="固定週期秒數，適用於 cycle_time")
    isActive = Column("is_active", Boolean, nullable=False, server_default="1", comment="是否啟用")
    description = Column(String(255), nullable=True, comment="排程描述")
    lastRunAt = Column("last_run_at", DateTime, nullable=True, comment="上次執行時間")
    nextRunAt = Column("next_run_at", DateTime, nullable=True, comment="下次預計執行時間")
