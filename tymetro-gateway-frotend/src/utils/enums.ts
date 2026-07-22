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

