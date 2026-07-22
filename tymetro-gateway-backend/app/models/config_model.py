from sqlalchemy import Column, String, Text
from app.models.base import AuditModel, IdType

class Config(AuditModel):
    __tablename__ = "configs"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    configType = Column("config_type", String(50), nullable=False, index=True, comment="設定類型 (例如: 時段設定、設備參數等)")
    configContent = Column("config_content", Text, nullable=True, comment="設定內容 (JSON 字串或純文字)")
