from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime, func
from sqlalchemy.orm import synonym
from app.models.base import IdType
from app.database.session import Base

class SettingLog(Base):
    """設定紀錄資料表 (setting_logs)"""
    __tablename__ = "setting_logs"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    settingType = Column("setting_type", String(50), nullable=False, comment="設定類型 (如: 溫度, 新鮮空氣擋板開度, 開啟緊急供氣擋板, 重置2/3)")
    value = Column(String(255), default=None, nullable=True, comment="設定數值或內容")
    operator = Column(String(100), default=None, nullable=True, comment="操作人員")
    isNotified = Column("is_notified", Boolean, nullable=False, default=False, server_default="0", comment="是否已通知")
    topic = Column(String(255), default=None, nullable=True, comment="MQTT Topic")
    payload = Column(Text, default=None, nullable=True, comment="MQTT Payload")
    commandId = Column("command_id", String(36), nullable=True, index=True, comment="指令關聯 ID (UUID)，與雲端 setting_logs.command_id 對應")
    status = Column("status", String(20), nullable=True, comment="指令狀態 (ACKED/SUCCESS/FAILED)，無 commandId 的紀錄為 NULL")
    errorMessage = Column("error_message", String(500), nullable=True, comment="失敗原因")
    ackedAt = Column("acked_at", DateTime, nullable=True, comment="gateway 收到指令時間")
    finishedAt = Column("finished_at", DateTime, nullable=True, comment="指令結束時間 (成功/失敗)")
    auditCategory = Column("audit_category", String(50), nullable=True, index=True, comment="審計類別 (例如: auth, modbus, schedule, system)，非審計紀錄為 NULL")
    action = Column(String(100), nullable=True, comment="審計操作動作 (例如: login, write_register, plc_sync)")
    ipAddress = Column("ip_address", String(50), nullable=True, comment="來源 IP 位址")
    detail = Column(String(1000), nullable=True, comment="審計詳細資訊或異常錯誤訊息")
    recordedAt = Column("recorded_at", DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(), comment="操作時間")
    timestamp = synonym("recordedAt")
