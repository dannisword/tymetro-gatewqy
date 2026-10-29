from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Optional
from datetime import datetime
from app.core.enums import get_setting_type_label

class SettingLogBase(BaseModel):
    settingType: str = Field(..., description="設定類型 (如: 溫度, 新鮮空氣擋板開度, 開啟緊急供氣擋板, 重置2/3)")
    value: Optional[str] = Field(None, description="設定數值或內容")
    operator: Optional[str] = Field(None, description="操作人員")
    isNotified: Optional[bool] = Field(default=False, description="是否已通知")
    topic: Optional[str] = Field(None, description="MQTT Topic")
    payload: Optional[str] = Field(None, description="MQTT Payload")
    commandId: Optional[str] = Field(None, description="指令關聯 ID (UUID)")
    status: Optional[str] = Field(None, description="指令狀態 (ACKED/SUCCESS/FAILED)")
    errorMessage: Optional[str] = Field(None, description="失敗原因")
    ackedAt: Optional[datetime] = Field(None, description="gateway 收到指令時間")
    finishedAt: Optional[datetime] = Field(None, description="指令結束時間")
    auditCategory: Optional[str] = Field(None, description="審計類別，非審計紀錄為 NULL")
    action: Optional[str] = Field(None, description="審計操作動作")
    ipAddress: Optional[str] = Field(None, description="來源 IP 位址")
    detail: Optional[str] = Field(None, description="審計詳細資訊或異常錯誤訊息")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SettingLogCreate(SettingLogBase):
    pass

class SettingLogUpdate(BaseModel):
    settingType: Optional[str] = None
    value: Optional[str] = None
    operator: Optional[str] = None
    isNotified: Optional[bool] = None
    topic: Optional[str] = None
    payload: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SettingLogResponse(SettingLogBase):
    id: int
    recordedAt: datetime = Field(..., description="操作時間")

    @computed_field(description="設定項目中文名稱")
    @property
    def settingTypeName(self) -> Optional[str]:
        return get_setting_type_label(self.settingType)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
