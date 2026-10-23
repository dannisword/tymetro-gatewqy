from sqlalchemy import Column, String, SmallInteger, Boolean, UniqueConstraint
from app.models.base import AuditModel, IdType

class EventTemplate(AuditModel):
    """PLC 暫存器點位樣板 (自中心端下載)：定義各暫存器 Bit (0~15) 的名稱、描述、事件類別與嚴重程度"""
    __tablename__ = "event_templates"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    templateCode = Column("template_code", String(50), nullable=False, default="HVAC_PLC_STANDARD", comment="樣板代碼")
    registerCode = Column("register_code", String(50), nullable=False, comment="暫存器代碼 (例如: D40016)")
    bitIndex = Column("bit_index", SmallInteger, nullable=False, comment="位元編號 (0~15)")
    tagName = Column("tag_name", String(50), nullable=False, comment="點位標籤")
    tagDesc = Column("tag_desc", String(100), nullable=False, comment="中文描述")
    eventType = Column("event_type", String(30), nullable=False, default="ALARM", comment="事件類別")
    severity = Column("severity", String(20), nullable=False, default="ERROR", comment="嚴重等級")
    isActive = Column("is_active", Boolean, nullable=False, default=True, server_default="1", comment="是否啟用")
    needConfirm = Column("need_confirm", Boolean, nullable=False, default=False, server_default="0", comment="是否需要確認")

    __table_args__ = (
        UniqueConstraint("template_code", "register_code", "bit_index", name="uk_template_reg_bit"),
    )
