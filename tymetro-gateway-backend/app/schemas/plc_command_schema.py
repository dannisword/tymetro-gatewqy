from pydantic import BaseModel, Field
from typing import Optional


class PlcCommandRequest(BaseModel):
    command: str = Field(..., description="執行的設定類型 (SettingType，可用指令定義於 plc_command_service.COMMANDS)")
    carNo: int = Field(..., description="車廂編號 (carVin，如 1101)")
    endPos: int = Field(..., ge=1, description="端點位置")
    trainCode: Optional[str] = Field(None, description="車組代碼 (未帶入時取自車廂資料)")
    value: Optional[float] = Field(None, description="設定值 (觸發型指令不需帶入)")


class PlcCommandResponse(BaseModel):
    command: str
    commandName: Optional[str] = None
    trainCode: str
    carNo: int
    endPos: int
    topic: str
    registers: dict
    settingLogId: Optional[int] = None
    # 需完成確認的指令：True 已完成 / False 逾時未完成 / None 無需或無法確認
    confirmed: Optional[bool] = None
    confirmMessage: Optional[str] = None
