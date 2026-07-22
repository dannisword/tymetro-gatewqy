from sqlalchemy import Column, Integer, BigInteger, DateTime, func
from app.database.session import Base
from app.core.config import settings

# 動態判斷 ID 型別：開發/單機版用 Integer (對 SQLite 較友善)，網路版用 BigInteger
IdType = Integer if settings.APP_MODE in ["development", "standalone"] else BigInteger

class AuditModel(Base):
    """
    提供共通稽核欄位的抽象類別
    """
    __abstract__ = True

    createdAt = Column("created_at", DateTime, default=func.now(), server_default=func.now(), comment="建立日期")
    createdBy = Column("created_by", IdType, default=0, server_default="0", nullable=False, comment="建立人員Seq")
    updatedAt = Column("updated_at", DateTime, default=func.now(), server_default=func.now(), onupdate=func.now(), comment="異動日期")
    updatedBy = Column("updated_by", IdType, default=0, server_default="0", nullable=False, comment="異動人員Seq")
