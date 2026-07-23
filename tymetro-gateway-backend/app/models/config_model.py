from sqlalchemy import Column, String, Text
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

