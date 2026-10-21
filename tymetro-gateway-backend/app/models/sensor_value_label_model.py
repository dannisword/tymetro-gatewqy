from sqlalchemy import Column, String, Integer
from app.models.base import AuditModel, IdType

class SensorValueLabel(AuditModel):
    """感測器位元/數值對照表 (自中心端下載)
    - 數值對照列：(暫存器值 & bit_mask) == match_value 時顯示 text
    - 位元名稱列 (text、match_value 皆為 NULL)：bit_mask 為單一 bit，label/description 即該位元的名稱與描述
    """
    __tablename__ = "sensor_value_labels"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    sensorCode = Column("sensor_code", String(50), nullable=False, index=True, comment="感測器編號")
    bitMask = Column("bit_mask", Integer, nullable=False, comment="判定位元遮罩")
    matchValue = Column("match_value", Integer, nullable=True, comment="遮罩後的比對值 (位元名稱列為 NULL)")
    text = Column(String(100), nullable=True, comment="顯示文字 (位元名稱列為 NULL)")
    label = Column(String(100), nullable=True, comment="群組名稱 (如信號名稱)")
    description = Column(String(200), nullable=True, comment="詳細描述")
