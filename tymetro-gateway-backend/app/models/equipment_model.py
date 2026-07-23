from sqlalchemy import Column, String, Integer, Date, Boolean, DateTime, ForeignKey
from app.models.base import AuditModel, IdType

class Equipment(AuditModel):
    """設備表 (equipments)"""
    __tablename__ = "equipments"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    carId = Column("car_id", IdType, ForeignKey("cars.id"), nullable=False, comment="車廂 ID")
    endPos = Column("end_pos", Integer, nullable=False, comment="端點位置 (1端或2端)")
    equipmentName = Column("equipment_name", String(50), nullable=False, comment="設備名稱")
    equipmentStatus = Column("equipment_status", String(50), nullable=False, default="OPERATING", comment="設備狀態")
    ipAddress = Column("ip_address", String(20), nullable=True, comment="網路位址")
    brandModel = Column("brand_model", String(100), nullable=True, comment="廠牌型號")
    installDate = Column("install_date", Date, nullable=True, comment="安裝日期")
    accumulatedHours = Column("accumulated_hours", Integer, default=0, comment="累積運轉時數 (小時)")
    isActive = Column("is_active", Boolean, nullable=False, default=True, server_default="1", comment="是否合法/啟用")
    lastSeenAt = Column("last_seen_at", DateTime, nullable=True, comment="最後通訊時間")
