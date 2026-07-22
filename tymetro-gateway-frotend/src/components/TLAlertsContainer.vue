<!-- components/AlertContainer.vue -->
<script setup lang="ts">
import { useAlert } from "../composables/TLAlter";
import BaseIcon from "../components/BaseIcon.vue";

const { alerts, closeAlert } = useAlert();

const positions = [
  "top-left",
  "top-center",
  "top-right",
  "bottom-left",
  "bottom-center",
  "bottom-right",
] as const;

const positionClass = (pos: string) => {
  const top = "top-4";
  const map: Record<string, string> = {
    "top-left": `${top} left-4 items-start`,
    "top-center": `${top} left-1/2 -translate-x-1/2 items-center`,
    "top-right": `${top} right-4 items-end`,
    "bottom-left": "bottom-6 left-4 items-start",
    "bottom-center": "bottom-6 left-1/2 -translate-x-1/2 items-center",
    "bottom-right": "bottom-6 right-4 items-end",
  };
  return map[pos];
};

const alertTypeClass = (type: string) => {
  const map: Record<string, string> = {
    success: "alert-success",
    error: "alert-error",
    info: "alert-info",
    warning: "alert-warning",
  };
  return map[type] || "alert-info";
};

const alertIcon = (type: string) => {
  const map: Record<string, string> = {
    success: "mdiCheckCircle",
    error: "mdiAlertCircle",
    info: "mdiInformation",
    warning: "mdiAlert",
  };
  return map[type];
};
</script>

<template>
  <div>
    <div 
      v-for="pos in positions" 
      :key="pos" 
      :class="['fixed z-[9999] flex flex-col gap-3 p-4 pointer-events-none', positionClass(pos)]"
    >
      <TransitionGroup name="alert-list">
        <div 
          v-for="alert in alerts.filter((a: any) => a.position === pos)" 
          :key="alert.id"
          :class="['alert-box pointer-events-auto', alertTypeClass(alert.type)]"
        >
          <div class="flex items-center gap-3">
            <div class="icon-wrapper">
              <BaseIcon :path="alertIcon(alert.type)" size="20" />
            </div>
            <span class="message-text">{{ alert.message }}</span>
          </div>
          
          <button @click="closeAlert(alert.id)" class="close-btn group">
            <span class="opacity-40 group-hover:opacity-100 transition-opacity">✕</span>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
.alert-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 320px;
  max-width: 450px;
  padding: 12px 18px;
  border-radius: 14px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.08);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.15);
}

.message-text {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.close-btn {
  padding: 4px;
  font-size: 12px;
  cursor: pointer;
  opacity: 0.5;
}

/* Success - Soft Emerald */
.alert-success {
  background-color: rgba(236, 252, 242, 0.6); /* emerald-50/60 */
  color: #15803d; /* emerald-700 */
  border: 1px solid rgba(34, 197, 94, 0.2);
}

/* Error - Soft Rose */
.alert-error {
  background-color: rgba(254, 242, 242, 0.6); /* red-50/60 */
  color: #b91c1c; /* red-700 */
  border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Info - Soft Sky */
.alert-info {
  background-color: rgba(239, 246, 255, 0.6); /* blue-50/60 */
  color: #1d4ed8; /* blue-700 */
  border: 1px solid rgba(59, 130, 246, 0.2);
}

/* Warning - Soft Amber */
.alert-warning {
  background-color: rgba(255, 251, 235, 0.7); /* amber-50/70 */
  color: #b45309; /* amber-700 */
  border: 1px solid rgba(245, 158, 11, 0.2);
}

/* Animation */
.alert-list-enter-from {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}
.alert-list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
.alert-list-enter-active,
.alert-list-leave-active {
  transition: all 0.3s ease;
}

/* Icon Wrapper Effect - Softened */
.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 10px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
}
</style>
