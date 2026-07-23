from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class OutboxBase(BaseModel):
    payload: str = Field(..., description="暫存 JSON 數據內容")
    createdAt: Optional[float] = Field(None, description="建立 Unix 時間戳 (秒)")
    retryCount: Optional[int] = Field(0, description="重試發送次數")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class OutboxCreate(BaseModel):
    payload: Dict[str, Any] = Field(..., description="待暫存發送的數據字典")
    createdAt: Optional[float] = Field(None, description="建立 Unix 時間戳 (秒)")

class OutboxUpdate(BaseModel):
    payload: Optional[str] = None
    retryCount: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class OutboxResponse(OutboxBase):
    id: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
