from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date
from app.schemas.base import AuditBase

class SensorBase(BaseModel):
    carId: int = Field(..., description="所屬車廂 ID")
    equipmentId: Optional[int] = Field(None, description="所屬設備 ID")
    sensorType: str = Field(..., description="感測器類型")
    sensorCode: str = Field(..., description="感測器編號")
    sensorName: str = Field(..., description="感測器名稱")
    sensorValue: float = Field(default=0.0, description="感測器數值")
    sensorUnit: str = Field(..., description="感測器單位")
    sensorStatus: Optional[str] = Field(default="OPERATING", description="狀態")
    calibrationOffset: Optional[float] = Field(default=0.00, description="校正偏移值")
    lastCalibrationDate: Optional[date] = Field(None, description="最後校正日期")
    showOnDashboard: Optional[bool] = Field(default=True, description="是否顯示在儀表板")
    isActive: Optional[bool] = Field(default=True, description="是否合法/啟用")
    saveHistory: Optional[bool] = Field(default=True, description="是否記錄歷史紀錄")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SensorCreate(SensorBase):
    pass

class SensorUpdate(BaseModel):
    carId: Optional[int] = None
    equipmentId: Optional[int] = None
    sensorType: Optional[str] = None
    sensorCode: Optional[str] = None
    sensorName: Optional[str] = None
    sensorValue: Optional[float] = None
    sensorUnit: Optional[str] = None
    sensorStatus: Optional[str] = None
    calibrationOffset: Optional[float] = None
    lastCalibrationDate: Optional[date] = None
    showOnDashboard: Optional[bool] = None
    isActive: Optional[bool] = None
    saveHistory: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SensorResponse(SensorBase, AuditBase):
    id: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
