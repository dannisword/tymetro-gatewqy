<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useLoadingStore } from "../store/useLoadingStore";
import BaseIcon from "./BaseIcon.vue";
import { mdiLoading } from "@mdi/js";

const { active } = storeToRefs(useLoadingStore());
</script>

<template>
  <transition name="fade" mode="out-in">
    <div
      v-if="active"
      class="pointer-events-auto fixed inset-0 z-[9999] flex items-center justify-center bg-white/10 backdrop-blur-sm"
    >
      <div
        class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow"
      >
        <BaseIcon
          :path="mdiLoading"
          class="animate-spin text-primary-600"
          :size="22"
        />
        <span class="text-sm text-slate-700">載入中…</span>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
