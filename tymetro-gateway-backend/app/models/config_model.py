from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import AuditModel, IdType

class Config(AuditModel):
    """舊版相容 Config"""
    __tablename__ = "configs"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    configType = Column("config_type", String(50), nullable=False, index=True, comment="設定類型")
    configContent = Column("config_content", Text, nullable=True, comment="設定內容")

class SystemConfig(AuditModel):
    """系統層級設定 (Gateway ID, Central Server, IPC Socket Path...)"""
    __tablename__ = "system_configs"

    id = Column(IdType, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True, comment="分類: gateway, network, database")
    key = Column(String(100), nullable=False, unique=True, index=True, comment="設定鍵值")
    value = Column(Text, nullable=False, comment="設定內容")
    description = Column(String(255), nullable=True, comment="說明")

class DeviceConfigModel(AuditModel):
    """PFC 控制器設備配置"""
    __tablename__ = "device_configs"

    id = Column(IdType, primary_key=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, unique=True, index=True, comment="設備 ID (如 PFC001)")
    name = Column(String(100), nullable=False, comment="設備名稱")
    ip = Column(String(50), nullable=False, comment="IP 位址")
    port = Column(Integer, default=502, comment="Modbus TCP Port")
    slave_id = Column(Integer, default=1, comment="Modbus Slave ID")
    is_active = Column(Boolean, default=True, comment="是否啟用輪詢")

    registers = relationship("RegisterConfigModel", back_populates="device", cascade="all, delete-orphan")

class RegisterConfigModel(AuditModel):
    """Modbus 暫存器點位配置"""
    __tablename__ = "register_configs"

    id = Column(IdType, primary_key=True, autoincrement=True)
    device_id = Column(String(50), ForeignKey("device_configs.device_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False, comment="點位名稱 (如 temp, humidity)")
    address = Column(Integer, nullable=False, comment="Modbus 暫存器位址")
    data_type = Column(String(20), default="INT16", comment="資料型態: INT16, UINT16, FLOAT32")
    scale = Column(Float, default=1.0, comment="縮放比例")
    unit = Column(String(20), default="", comment="單位")

    device = relationship("DeviceConfigModel", back_populates="registers")
