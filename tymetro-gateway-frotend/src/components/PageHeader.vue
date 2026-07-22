<!-- src/components/PageHeader.vue -->
<script setup lang="ts">
import { mdiRefresh } from "@mdi/js";
import BaseButton from "@/components/BaseButton.vue";

const props = withDefaults(
  defineProps<{
    title: string;
    count?: number;
    countUnit?: string;
    subtitle?: string;
    lastUpdated?: string;
    showRefresh?: boolean;
    loading?: boolean;
    isConnected?: boolean;
  }>(),
  {
    count: undefined,
    countUnit: "Units",
    subtitle: "系統即時數據監控",
    lastUpdated: "",
    showRefresh: false,
    loading: false,
    isConnected: false,
  }
);

const emit = defineEmits(["refresh"]);
</script>

<template>
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200/60 shadow-sm mb-8">
    <div>
      <h1 class="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-3">
        {{ title }}
        <span 
          v-if="count !== undefined" 
          class="text-xs font-bold bg-[#2a7eb5]/10 text-[#2a7eb5] px-2.5 py-1 rounded-full uppercase tracking-wider"
        >
          {{ count }} {{ countUnit }}
        </span>
      </h1>
      <div class="flex items-center gap-4 mt-2">
        <span class="text-xs font-semibold text-slate-400">{{ subtitle }}</span>
        <template v-if="lastUpdated">
          <span class="text-xs text-slate-300">|</span>
          <span class="text-xs font-semibold text-slate-400">最後更新時間: {{ lastUpdated }}</span>
        </template>
      </div>
    </div>

    <div class="flex items-center gap-3 shrink-0">
      <!-- MQTT status -->
      <div 
        :class="[
          'flex items-center gap-3 px-5 py-2 rounded-full border shadow-sm transition-all duration-300',
          isConnected 
            ? 'bg-slate-50/80 border-slate-200/60 shadow-slate-100/50' 
            : 'bg-slate-50/80 border-slate-200/60 shadow-slate-100/50 animate-pulse'
        ]"
      >
        <div 
          :class="[
            'w-5 h-5 rounded-full transition-colors duration-300',
            isConnected ? 'bg-emerald-500' : 'bg-rose-500'
          ]"
        ></div>
        <span 
          :class="[
            'text-lg font-black tracking-wider uppercase transition-colors duration-300',
            isConnected ? 'text-emerald-700' : 'text-rose-600'
          ]"
        >
          MQTT
        </span>
      </div>

      <!-- Refresh Button -->
      <BaseButton
        v-if="showRefresh"
        @click="emit('refresh')"
        variant="default"
        mode="outline"
        circle
        icon-only
        :icon="mdiRefresh"
        :loading="loading"
        class="!p-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200/60 transition-all active:scale-95 shadow-sm text-slate-600"
        title="重新整理"
      />
    </div>
  </div>
</template>
