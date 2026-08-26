from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime, func
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
    recordedAt = Column("recorded_at", DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(), comment="操作時間")
