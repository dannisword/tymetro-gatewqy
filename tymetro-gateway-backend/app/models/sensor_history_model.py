from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.models.base import IdType
from app.database.session import Base

class SensorHistory(Base):
    """感測器歷史資料表 (sensor_histories)"""
    __tablename__ = "sensor_histories"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    carId = Column("car_id", Integer, nullable=False, default=0, comment="車廂 ID / 車廂號")
    carVin = Column("car_vin", String(50), nullable=True, comment="車廂唯一識別碼/車號")
    carNo = Column("car_no", Integer, nullable=True, comment="車廂序號")
    endPos = Column("end_pos", Integer, nullable=True, comment="端點位置 (1端或2端，可為空)")
    sensorCode = Column("sensor_code", String(50), nullable=False, comment="感測器點位代碼")
    sensorValue = Column("sensor_value", Float, nullable=False, comment="感測器數值")
    recordedAt = Column("recorded_at", DateTime, index=True, nullable=False, default=datetime.utcnow, server_default=func.now(), comment="記錄時間")
    sensorName = Column("sensor_name", String(100), nullable=True, comment="感測器名稱")
    sensorUnit = Column("sensor_unit", String(10), nullable=True, comment="感測器單位")
    equipmentName = Column("equipment_name", String(100), nullable=True, comment="設備名稱")
