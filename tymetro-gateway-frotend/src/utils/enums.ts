export enum FormMode {
  None = "None",
  Add = "Add",
  Edit = "Edit",
  Cancel = "Cancel",
  Back = "Back",
  Delete = "Delete",
  Save = "Save",
  Copy = "Copy",
  Confirm = "Confirm",
  Refresh = "Refresh",
  Menu = "Menu",
  Close = "Close",
}

export const SYSTEM_MODE_MAP = {
  0: "停止",
  1: "測試",
  2: "自動",
  3: "送風"
} as const;

export type SystemModeKey = keyof typeof SYSTEM_MODE_MAP;

export enum CompressorStatus {
  ON = "ON",
  OFF = "OFF",
}

export enum CompressorHealth {
  Normal = "正常",
  Abnormal = "異常",
}

export enum AuditCategory {
  Schedule = "schedule",
  User = "user",
  Auth = "auth",
  System = "system",
  Modbus = "modbus",
  Enum = "enum",
}

export enum SettingTypeEnum {
  TEMPERATURE = "TEMPERATURE",
  FRESH_AIR_DAMPER = "FRESH_AIR_DAMPER",
  EMERGENCY_AIR_SUPPLY = "EMERGENCY_AIR_SUPPLY",
  RESET_ALL = "RESET_ALL",
  INITIAL_VALUE = "INITIAL_VALUE", // 初始值 (D40216，觸發；D40217 完成)
  MANUAL_START_AC = "MANUAL_START_AC", // 手動開啟空調系統 (D40218，觸發；D40219 完成)
  FORCE_EMERGENCY_DAMPER = "FORCE_EMERGENCY_DAMPER", // 強制開啟緊急供氣擋板 (D40220，觸發；D40221 完成)
  FORCE_EXCHANGER = "FORCE_EXCHANGER", // 強制開啟換流器 (D40222，觸發；D40223 完成)
  CLEAR_COMP1_HOURS = "CLEAR_COMP1_HOURS", // 清除壓縮機1運轉時數 (D40224，觸發；D40225 完成)
  CLEAR_COMP2_HOURS = "CLEAR_COMP2_HOURS", // 清除壓縮機2運轉時數 (D40226，觸發；D40227 完成)
  CLEAR_AC_HOURS = "CLEAR_AC_HOURS", // 清除空調運轉時數 (D40228，觸發；D40229 完成)
}

