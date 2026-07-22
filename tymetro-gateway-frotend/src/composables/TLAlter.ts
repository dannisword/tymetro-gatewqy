// composables/useAlert.ts
import { ref } from "vue";

export type AlertPosition =
  | "top-left"
  | "top-center"
  | "top-right"
  | "bottom-left"
  | "bottom-center"
  | "bottom-right";

export type AlertType = "success" | "error" | "info" | "warning";

export interface Alert {
  id: number;
  message: string;
  type: AlertType;
  position: AlertPosition;
  timeout?: number;
}

const alerts = ref<Alert[]>([]);
let idCounter = 0;

export function useAlert() {
  const TLSuccess = (
    message: string,
    position: AlertPosition = "bottom-center",
    timeout = 5000
  ) => {
    showAlert(message, "success", position, timeout);
  };
  const TLInfo = (
    message: string,
    position: AlertPosition = "bottom-center",
    timeout = 5000
  ) => {
    showAlert(message, "info", position, timeout);
  };
  const TLWarning = (
    message: string,
    position: AlertPosition = "bottom-center",
    timeout = 0
  ) => {
    showAlert(message, "warning", position, timeout);
  };
  const TLError = (
    message: string,
    position: AlertPosition = "bottom-center",
    timeout = 0
  ) => {
    showAlert(message, "error", position, timeout);
  };
  const showAlert = (
    message: string,
    type: AlertType,
    position: AlertPosition = "bottom-center",
    timeout = 5000
  ) => {
    const id = idCounter++;
    const alert: Alert = { id, message, type, position, timeout };
    alerts.value.push(alert);

    if (timeout > 0) {
      setTimeout(() => closeAlert(id), timeout);
    }
  };

  const closeAlert = (id: number) => {
    alerts.value = alerts.value.filter((alert) => alert.id !== id);
  };

  return { alerts, TLSuccess, TLInfo, TLWarning, TLError, closeAlert };
}
