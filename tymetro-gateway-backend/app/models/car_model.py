from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.models.base import AuditModel, IdType

class Car(AuditModel):
    """車廂表 (cars)"""
    __tablename__ = "cars"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    trainCode = Column("train_code", String(20), nullable=False, comment="車組編號 (如 AC-105)")
    carNo = Column("car_no", Integer, nullable=False, comment="車廂序號 (1, 2, 3, 4)")
    carVin = Column("car_vin", String(50), nullable=True, unique=True, comment="車廂唯一識別碼/車號")
    carType = Column("car_type", String(20), nullable=True, comment="車廂類型 (EXPRESS, COMMUTER)")
    carTag = Column("car_tag", String(20), nullable=True, comment="車廂標籤")
    carStatus = Column("car_status", String(20), nullable=True, comment="狀態 (OPERATING, MAINTENANCE, IDLE, OFFLINE, ABNORMAL)")
    isActive = Column("is_active", Boolean, nullable=False, default=True, server_default="1", comment="是否合法/啟用")
    lastSeenAt = Column("last_seen_at", DateTime, nullable=True, comment="最後通訊時間")
