<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import BaseIcon from "./BaseIcon.vue";
import {
  mdiCheckCircle,
  mdiAlertCircle,
  mdiInformation,
  mdiAlert,
} from "@mdi/js";

const props = defineProps({
  message: { type: String, required: true },
  title: { type: String, default: "提示" },
  confirmButtonText: { type: String, default: "確定" },
  cancelButtonText: { type: String, default: "取消" },
  showCancelButton: { type: Boolean, default: true },
  showClose: { type: Boolean, default: true },
  type: { type: String, default: "info" }, // 'success' | 'warning' | 'info' | 'error'
  closeOnClickModal: { type: Boolean, default: false },
});

const emit = defineEmits(["resolve", "reject", "vanish"]);

const visible = ref(false);
let actionResult: "confirm" | "cancel" | "close" = "cancel";

onMounted(() => {
  // Trigger entry animation
  visible.value = true;
});

const iconPath = computed(() => {
  switch (props.type) {
    case "success":
      return mdiCheckCircle;
    case "warning":
      return mdiAlert;
    case "error":
      return mdiAlertCircle;
    case "info":
    default:
      return mdiInformation;
  }
});

const iconColorClass = computed(() => {
  switch (props.type) {
    case "success":
      return "text-emerald-500 dark:text-emerald-400";
    case "warning":
      return "text-amber-500 dark:text-amber-400";
    case "error":
      return "text-rose-500 dark:text-rose-400";
    case "info":
    default:
      return "text-primary dark:text-primary";
  }
});

const confirmButtonClass = computed(() => {
  switch (props.type) {
    case "success":
      return "bg-emerald-500 hover:bg-emerald-600 dark:bg-emerald-600 dark:hover:bg-emerald-700 shadow-emerald-500/20";
    case "warning":
      return "bg-amber-500 hover:bg-amber-600 dark:bg-amber-600 dark:hover:bg-amber-700 shadow-amber-500/20";
    case "error":
      return "bg-rose-500 hover:bg-rose-600 dark:bg-rose-600 dark:hover:bg-rose-700 shadow-rose-500/20";
    case "info":
    default:
      return "bg-primary hover:opacity-95 shadow-primary/20";
  }
});

const handleAction = (action: "confirm" | "cancel" | "close") => {
  actionResult = action;
  visible.value = false;
};

const handleBackdropClick = () => {
  if (props.closeOnClickModal) {
    handleAction("cancel");
  }
};

const handleAfterLeave = () => {
  if (actionResult === "confirm") {
    emit("resolve", "confirm");
  } else {
    emit("reject", actionResult);
  }
  emit("vanish");
};
</script>

<template>
  <div class="fixed inset-0 z-[9999] flex items-center justify-center p-4">
    <!-- Backdrop Overlay -->
    <transition name="fade" appear>
      <div
        v-if="visible"
        class="absolute inset-0 bg-slate-900/40 dark:bg-slate-950/65 backdrop-blur-[2px] transition-opacity duration-200"
        @click="handleBackdropClick"
      ></div>
    </transition>

    <!-- Dialog Box Container -->
    <transition name="zoom" appear @after-leave="handleAfterLeave">
      <div
        v-if="visible"
        class="relative w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden flex flex-col z-10 transform transition-all duration-200"
      >
        <!-- Header Section -->
        <div class="flex items-center justify-between px-5 pt-5 pb-3">
          <h3 class="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <!-- Icon -->
            <span :class="iconColorClass" class="flex items-center justify-center">
              <BaseIcon :path="iconPath" size="22" />
            </span>
            <span>{{ title }}</span>
          </h3>
          <!-- Close button -->
          <button
            v-if="showClose"
            @click="handleAction('close')"
            class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50"
          >
            <span class="text-xs leading-none">✕</span>
          </button>
        </div>

        <!-- Body Content Section -->
        <div class="px-5 pb-5 text-slate-600 dark:text-slate-300 text-sm leading-relaxed flex-1">
          <p class="whitespace-pre-wrap font-medium">{{ message }}</p>
        </div>

        <!-- Footer Buttons Section -->
        <div class="px-5 py-3.5 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-700/50 flex justify-end gap-2.5">
          <button
            v-if="showCancelButton"
            @click="handleAction('cancel')"
            class="px-4 py-2 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700/80 rounded-lg text-sm text-slate-600 dark:text-slate-300 transition-all font-semibold"
          >
            {{ cancelButtonText }}
          </button>
          <button
            @click="handleAction('confirm')"
            class="px-5 py-2 rounded-lg text-sm text-white font-semibold shadow-lg transition-all active:scale-[0.98] flex items-center justify-center"
            :class="confirmButtonClass"
          >
            {{ confirmButtonText }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* Fade Transition (Backdrop) */
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease-out;
}

/* Zoom/Scale Transition (Dialog Box) */
.zoom-enter-from,
.zoom-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
.zoom-enter-active,
.zoom-leave-active {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease-out;
}
</style>
