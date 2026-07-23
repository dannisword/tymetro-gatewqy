from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from app.schemas.base import AuditBase

class CarBase(BaseModel):
    trainCode: str = Field(..., description="車組編號 (如 AC-105)")
    carNo: int = Field(..., description="車廂序號 (1, 2, 3, 4)")
    carVin: Optional[str] = Field(None, description="車廂唯一識別碼/車號")
    carType: Optional[str] = Field(None, description="車廂類型 (EXPRESS, COMMUTER)")
    carTag: Optional[str] = Field(None, description="車廂標籤")
    carStatus: Optional[str] = Field(None, description="狀態 (OPERATING, MAINTENANCE, IDLE, OFFLINE, ABNORMAL)")
    isActive: Optional[bool] = Field(True, description="是否合法/啟用")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class CarCreate(CarBase):
    pass

class CarUpdate(BaseModel):
    trainCode: Optional[str] = None
    carNo: Optional[int] = None
    carVin: Optional[str] = None
    carType: Optional[str] = None
    carTag: Optional[str] = None
    carStatus: Optional[str] = None
    isActive: Optional[bool] = None
    lastSeenAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class CarResponse(CarBase, AuditBase):
    id: int
    lastSeenAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
