from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from app.schemas.base import AuditBase

class ScheduleBase(BaseModel):
    name: str = Field(..., description="排程名稱")
    scheduleType: str = Field(..., description="排程類型: hourly, minutely, fixed_time, cycle_time")
    taskCode: Optional[str] = Field(None, description="任務代碼 (例如: SYNC_DEVICE, MONITOR_ALARM)")
    cronExpression: Optional[str] = Field(None, description="Cron 表達式 (可選)")
    minuteOfHour: Optional[int] = Field(None, ge=0, le=59, description="每小時的第幾分鐘執行 (0-59)")
    secondOfMinute: Optional[int] = Field(None, ge=0, le=59, description="每分鐘的第幾秒執行 (0-59)")
    fixedTime: Optional[str] = Field(None, description="固定執行時間 (格式 HH:mm:ss)")
    cycleTime: Optional[int] = Field(None, ge=1, description="固定週期秒數")
    isActive: Optional[bool] = Field(True, description="是否啟用")
    description: Optional[str] = Field(None, description="排程描述")
    lastRunAt: Optional[datetime] = Field(None, description="上次執行時間")
    nextRunAt: Optional[datetime] = Field(None, description="下次預計執行時間")

    model_config = ConfigDict(from_attributes=True)

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="排程名稱")
    scheduleType: Optional[str] = Field(None, description="排程類型")
    taskCode: Optional[str] = Field(None, description="任務代碼")
    cronExpression: Optional[str] = Field(None, description="Cron 表達式")
    minuteOfHour: Optional[int] = Field(None, ge=0, le=59, description="每小時的第幾分鐘")
    secondOfMinute: Optional[int] = Field(None, ge=0, le=59, description="每分鐘的第幾秒")
    fixedTime: Optional[str] = Field(None, description="固定執行時間 (HH:mm:ss)")
    cycleTime: Optional[int] = Field(None, ge=1, description="固定週期秒數")
    isActive: Optional[bool] = Field(None, description="是否啟用")
    description: Optional[str] = Field(None, description="排程描述")
    lastRunAt: Optional[datetime] = Field(None, description="上次執行時間")
    nextRunAt: Optional[datetime] = Field(None, description="下次預計執行時間")

    model_config = ConfigDict(from_attributes=True)

class ScheduleResponse(ScheduleBase, AuditBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
