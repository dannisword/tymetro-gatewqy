import time
from sqlalchemy import Column, Integer, Text, Float
from app.database.session import Base
from app.models.base import IdType

class Outbox(Base):
    """Outbox 離線暫存資料表 (outbox)"""
    __tablename__ = "outbox"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    payload = Column(Text, nullable=False, comment="暫存 JSON 數據內容")
    createdAt = Column("created_at", Float, nullable=False, default=time.time, comment="建立 Unix 時間戳 (秒)")
    retryCount = Column("retry_count", Integer, default=0, server_default="0", comment="重試發送次數")
