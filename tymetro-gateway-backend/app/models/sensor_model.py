from sqlalchemy import Column, String, Float, Integer, Date, Boolean, ForeignKey
from app.models.base import AuditModel, IdType

class Sensor(AuditModel):
    """感測器配置與校正表 (sensors)"""
    __tablename__ = "sensors"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    carId = Column("car_id", IdType, ForeignKey("cars.id"), nullable=False, comment="所屬車廂")
    equipmentId = Column("equipment_id", IdType, ForeignKey("equipments.id"), nullable=True, comment="所屬設備")
    sensorType = Column("sensor_type", String(50), nullable=False, comment="感測器類型")
    sensorCode = Column("sensor_code", String(50), nullable=False, comment="感測器編號")
    sensorName = Column("sensor_name", String(50), nullable=False, comment="感測器名稱")
    sensorValue = Column("sensor_value", Float, nullable=False, default=0.0, comment="感測器數值")
    sensorUnit = Column("sensor_unit", String(10), nullable=False, comment="感測器單位")
    sensorStatus = Column("sensor_status", String(20), default="OPERATING", comment="狀態")
    calibrationOffset = Column("calibration_offset", Float, default=0.00, comment="校正偏移值")
    lastCalibrationDate = Column("last_calibration_date", Date, nullable=True, comment="最後校正日期")
    showOnDashboard = Column("show_on_dashboard", Boolean, nullable=False, default=True, server_default="1", comment="是否顯示在儀表板")
    isActive = Column("is_active", Boolean, nullable=False, default=True, server_default="1", comment="是否合法/啟用")
    saveHistory = Column("save_history", Boolean, nullable=False, default=True, server_default="1", comment="是否記錄歷史紀錄")
