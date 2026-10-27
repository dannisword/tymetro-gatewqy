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
    SETTING = ("setting", "設定控制")


class PlcEvent(LabeledEnum):
    """PLC 控制事件類型"""
    WRITE_TEMPERATURE = ("write_temperature", "設定溫度控制")
    WRITE_REGISTER = ("write_register", "寫入暫存器")
    SET_VALUE=("set_value", "設定數值")

class PlcRegister(LabeledEnum):
    """PLC 控制暫存器代碼"""
    TEMP_SETTING_CMD = ("D40200", "溫度設定命令 (x10)")
    TEMP_SETTING_FEEDBACK = ("D40201", "溫度設定反饋/完成 (x10)")
    TEMP_SETTING_DISPLAY = ("D40121", "溫度設定顯示點位")
    FRESH_AIR_DAMPER_CMD = ("D40212", "新鮮空氣擋板設定")
    FRESH_AIR_DAMPER_DISPLAY = ("D40213", "新鮮空氣擋板顯示")
    EMERG_AIR_DAMPER_CMD = ("D40214", "緊急供氣擋板設定")
    EMERG_AIR_DAMPER_DISPLAY = ("D40215", "緊急供氣擋板顯示")

class SettingType(LabeledEnum):
    """設定記錄類型"""
    TEMPERATURE = ("TEMPERATURE", "溫度設定")
    FRESH_AIR_DAMPER = ("FRESH_AIR_DAMPER", "新鮮空氣擋板開度")
    EMERGENCY_AIR_SUPPLY = ("EMERGENCY_AIR_SUPPLY", "緊急供氣擋板")
    RESET_ALL = ("RESET_ALL", "全車重置復歸")
    INITIAL_VALUE = ("INITIAL_VALUE", "初始值")  # D40216 觸發 / D40217 完成
    MANUAL_START_AC = ("MANUAL_START_AC", "手動開啟空調系統")  # D40218 觸發 / D40219 完成
    FORCE_EMERGENCY_DAMPER = ("FORCE_EMERGENCY_DAMPER", "強制開啟緊急供氣擋板")  # D40220 觸發 / D40221 完成
    FORCE_EXCHANGER = ("FORCE_EXCHANGER", "強制開啟換流器")  # D40222 觸發 / D40223 完成
    CLEAR_COMP1_HOURS = ("CLEAR_COMP1_HOURS", "清除壓縮機1運轉時數")  # D40224 觸發 / D40225 完成
    CLEAR_COMP2_HOURS = ("CLEAR_COMP2_HOURS", "清除壓縮機2運轉時數")  # D40226 觸發 / D40227 完成
    CLEAR_AC_HOURS = ("CLEAR_AC_HOURS", "清除空調運轉時數")  # D40228 觸發 / D40229 完成


# 相容別名
SettingTypeEnum = SettingType


def get_all_enums() -> Dict[str, Any]:
    """回傳系統所有列舉選項與對應表"""
    return {
        "sensorType": SensorType.to_options(),
        "sensorStatus": SensorStatus.to_options(),
        "endPos": EndPos.to_options(),
        "auditCategory": AuditCategory.to_options(),
        "plcEvent": PlcEvent.to_options(),
        "plcRegister": PlcRegister.to_options(),
        "categoryMap": AuditCategory.to_map(),
        "auditCategoryMap": AuditCategory.to_map(),
    }


