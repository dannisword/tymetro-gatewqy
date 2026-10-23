from sqlalchemy import Column, String, SmallInteger, Integer, DateTime, Boolean, func
from app.database.session import Base

class EquipmentEvent(Base):
    """設備狀態與警報變動事件紀錄表 (equipment_events)：僅在 PLC Word 特定 Bit 變更時寫入"""
    __tablename__ = "equipment_events"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="流水序")
    carVin = Column("car_vin", String(50), nullable=True, index=True, comment="車廂識別碼/車號")
    carNo = Column("car_no", SmallInteger, nullable=True, comment="車廂序號")
    endPos = Column("end_pos", SmallInteger, nullable=True, comment="端點位置")
    registerCode = Column("register_code", String(50), nullable=False, comment="暫存器代碼 (例如: D40016)")
    bitIndex = Column("bit_index", SmallInteger, nullable=False, comment="變動的位元編號 (0~15)")
    tagName = Column("tag_name", String(50), nullable=False, comment="點位標籤")
    tagDesc = Column("tag_desc", String(100), nullable=True, comment="中文描述")
    eventType = Column("event_type", String(30), nullable=False, default="ALARM", comment="事件類別")
    prevValue = Column("prev_value", SmallInteger, nullable=False, comment="變更前狀態")
    newValue = Column("new_value", SmallInteger, nullable=False, comment="變更後狀態")
    action = Column("action", String(20), nullable=False, comment="TRIGGERED / CLEARED / CHANGED / RESTORED")
    isConfirmed = Column("is_confirmed", Boolean, nullable=False, default=False, server_default="0", comment="確認旗標")
    triggeredAt = Column("triggered_at", DateTime, nullable=False, index=True, default=func.now(), server_default=func.now(), comment="變動發生時間")
