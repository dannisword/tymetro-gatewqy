from sqlalchemy import Column, String, DateTime
from app.models.base import IdType
from app.database.session import Base
from app.utils.datetime_util import get_local_now

class AuditLog(Base):
    """審計與系統異常日誌紀錄表"""
    __tablename__ = "audit_logs"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    auditCategory = Column("audit_category", String(50), nullable=False, index=True, comment="審計類別 (例如: auth, modbus, schedule, system)")
    action = Column(String(100), nullable=False, comment="操作動作 (例如: login, write_register, plc_sync)")
    status = Column(String(20), nullable=False, default="success", comment="執行狀態 (success: 成功, fail: 失敗)")
    operator = Column(String(100), nullable=True, comment="操作人員帳號/系統模組名稱")
    ipAddress = Column("ip_address", String(50), nullable=True, comment="來源 IP 位址")
    detail = Column(String(1000), nullable=True, comment="詳細資訊或異常錯誤訊息")
    timestamp = Column(DateTime, default=get_local_now, index=True, comment="紀錄時間")
