from datetime import datetime
from sqlalchemy import Column, Float, Integer, String, DateTime, func
from app.database.session import Base
from app.models.base import IdType


class PlcCommandTask(Base):
    """PLC 設定指令重試佇列 (plc_command_tasks)：批次設定未確認的端點，由背景 worker 重試至成功或達上限"""
    __tablename__ = "plc_command_tasks"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    command = Column(String(50), nullable=False, comment="設定類型 (SettingType)")
    value = Column(Float, nullable=True, comment="設定值")
    carNo = Column("car_no", Integer, nullable=False, comment="車號 (carVin 數字)")
    endPos = Column("end_pos", Integer, nullable=False, comment="端點")
    trainCode = Column("train_code", String(20), nullable=True, comment="車組代碼 (空值則由車廂資料帶入)")
    event = Column(String(50), nullable=True, comment="下發 events 欄位 (空值則用指令預設)")
    operator = Column(String(100), nullable=True, comment="原始操作人員")
    status = Column(String(20), nullable=False, default="PENDING", server_default="PENDING", index=True,
                    comment="PENDING / SUCCESS / FAILED (達上限) / SUPERSEDED (被新指令取代) / EXPIRED (逾 1 小時未執行)")
    attemptCount = Column("attempt_count", Integer, nullable=False, default=0, server_default="0", comment="已重試次數")
    maxAttempts = Column("max_attempts", Integer, nullable=False, default=10, server_default="10", comment="重試上限")
    lastError = Column("last_error", String(500), nullable=True, comment="最近一次未確認原因")
    createdAt = Column("created_at", DateTime, nullable=False, default=datetime.now, server_default=func.now(), comment="建立時間")
    updatedAt = Column("updated_at", DateTime, nullable=True, comment="最近一次重試/狀態變更時間")
