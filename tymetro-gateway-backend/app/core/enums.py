from enum import Enum
from typing import Any, Dict, List


class LabeledEnum(Enum):
    """具備顯示名稱 (label) 的列舉基底類別"""
    value: Any
    label: str

    def __new__(cls, value: Any, label: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Enum):
            return self.value == other.value
        return self.value == other

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def to_options(cls) -> List[Dict[str, Any]]:
        """轉換為前端通用選單格式 [{"value": ..., "label": ...}]"""
        return [{"value": item.value, "label": item.label} for item in cls]

    @classmethod
    def to_map(cls) -> Dict[str, str]:
        """轉換為前端字典對應格式 {value: label}"""
        return {str(item.value): item.label for item in cls}


class SensorType(LabeledEnum):
    """感測器類型"""
    INITIAL = ("INITIAL", "初始值")
    REAL_TIME = ("REAL_TIME", "即時值")
    SETTING = ("SETTING", "設定值")
    CONTROLLER_STATUS = ("CONTROLLER_STATUS", "控制器狀態")


class SensorStatus(LabeledEnum):
    """感測器狀態"""
    OPERATING = ("OPERATING", "運作中")
    MAINTENANCE = ("MAINTENANCE", "維修中")
    IDLE = ("IDLE", "閒置")
    OFFLINE = ("OFFLINE", "離線")
    ABNORMAL = ("ABNORMAL", "異常")


class EndPos(LabeledEnum):
    """端點位置 (車端)"""
    ONE = (1, "1端")
    TWO = (2, "2端")


class AuditCategory(LabeledEnum):
    """審計類別"""
    SCHEDULE = ("schedule", "系統排程")
    USER = ("user", "用戶管理")
    AUTH = ("auth", "身份驗證")
    SYSTEM = ("system", "系統日誌")

def get_all_enums() -> Dict[str, Any]:
    """回傳系統所有列舉選項與對應表"""
    return {
        "sensorType": SensorType.to_options(),
        "sensorStatus": SensorStatus.to_options(),
        "endPos": EndPos.to_options(),
        "auditCategory": AuditCategory.to_options(),
        "categoryMap": AuditCategory.to_map(),
        "auditCategoryMap": AuditCategory.to_map(),
    }

