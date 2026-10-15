from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class SensorHistoryResponse(BaseModel):
    id: int
    carId: Optional[int] = Field(None, description="車廂 ID")
    carVin: Optional[str] = Field(None, description="車廂唯一識別碼")
    carNo: Optional[int] = Field(None, description="車廂序號")
    endPos: Optional[int] = Field(None, description="端點位置 (1端或2端)")
    sensorCode: str = Field(..., description="感測器代碼")
    sensorValue: float = Field(..., description="感測器數值")
    recordedAt: datetime = Field(..., description="記錄時間")
    sensorName: Optional[str] = Field(None, description="感測器名稱")
    sensorUnit: Optional[str] = Field(None, description="感測器單位")
    equipmentName: Optional[str] = Field(None, description="設備名稱")
    scale: float = Field(1.0, description="縮放比例 (sensors.scale)")
    scaledValue: Optional[float] = Field(None, description="依 scale 換算後的數值 (sensorValue × scale)")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
