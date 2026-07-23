from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime
from app.schemas.base import AuditBase

class EquipmentBase(BaseModel):
    carId: int = Field(..., description="車廂 ID")
    endPos: int = Field(..., description="端點位置 (1端或2端)")
    equipmentName: str = Field(..., description="設備名稱")
    equipmentStatus: str = Field(default="OPERATING", description="設備狀態")
    ipAddress: Optional[str] = Field(None, description="網路位址")
    brandModel: Optional[str] = Field(None, description="廠牌型號")
    installDate: Optional[date] = Field(None, description="安裝日期")
    accumulatedHours: Optional[int] = Field(0, description="累積運轉時數 (小時)")
    isActive: Optional[bool] = Field(True, description="是否合法/啟用")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentUpdate(BaseModel):
    carId: Optional[int] = None
    endPos: Optional[int] = None
    equipmentName: Optional[str] = None
    equipmentStatus: Optional[str] = None
    ipAddress: Optional[str] = None
    brandModel: Optional[str] = None
    installDate: Optional[date] = None
    accumulatedHours: Optional[int] = None
    isActive: Optional[bool] = None
    lastSeenAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class EquipmentResponse(EquipmentBase, AuditBase):
    id: int
    lastSeenAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
