<script setup lang="ts">
import { computed } from 'vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { EndpointStatus } from '@/utils/types';
import { CompressorStatus } from '@/utils/enums';
import { routeHandle } from '@/hooks/route-handle';
import {
  mdiSnowflake,
  mdiWeatherWindy,
  mdiThermometer,
  mdiAirConditioner,
  mdiChevronRight
} from '@mdi/js';

const props = defineProps<{
  endpoint: EndpointStatus;
  carId: number;
}>();

const navigator = routeHandle().navigation;

const goToDetail = () => {
  navigator(`/mtr/single-end-pos/${props.carId}/${props.endpoint.id}`, `端點狀態-${props.carId}-${props.endpoint.id}`);
};

// 狀態顏色輔助計算
const statusClasses = computed(() => {
  const isEpConnected = props.endpoint.isConnected;
  const status = props.endpoint.status;

  if (!isEpConnected) {
    return {
      badge: 'bg-slate-100 text-slate-500 border border-slate-200',
      card: 'border-slate-200/60 bg-white/70 opacity-75'
    };
  }
  switch (status) {
    case 'normal':
      return {
        badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
        card: 'border-emerald-100 bg-white hover:border-emerald-300'
      };
    case 'warning':
      return {
        badge: 'bg-amber-50 text-amber-700 border border-amber-200',
        card: 'border-amber-100 bg-white hover:border-amber-300'
      };
    case 'abnormal':
      return {
        badge: 'bg-rose-50 text-rose-700 border border-rose-200',
        card: 'border-rose-100 bg-white hover:border-rose-300'
      };
    default:
      return {
        badge: 'bg-slate-50 text-slate-700 border border-slate-200',
        card: 'border-slate-200/60 bg-white'
      };
  }
});
</script>

<template>
  <div 
    :class="[
      'p-4 rounded-2xl border-2 transition-all duration-300 flex flex-col gap-3 group relative overflow-hidden',
      statusClasses.card
    ]"
  >
    <!-- 端點連線指示燈與標題 -->
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-2">
        <div :class="['w-2 h-2 rounded-full', endpoint.isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300']"></div>
        <h3 class="text-md font-black text-slate-700 leading-none">{{ endpoint.name }}</h3>
      </div>
      <span :class="['text-[12px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider', statusClasses.badge]">
        {{ endpoint.isConnected ? endpoint.statusName : '已離線' }}
      </span>
    </div>

    <!-- 核心溫度與模式參數 -->
    <div class="grid grid-cols-3 gap-2 bg-slate-50/50 p-2.5 rounded-xl border border-slate-100/50 text-center">
      <!-- 運轉模式 -->
      <div class="flex flex-col min-w-0">
        <span class="text-[12px] font-bold text-slate-400 uppercase tracking-tighter">模式</span>
        <span class="text-xs font-black text-slate-700 mt-1 truncate flex items-center justify-center gap-0.5">
          <template v-if="endpoint.isConnected">
            <BaseIcon v-if="endpoint.mode === '自動'" :path="mdiSnowflake" size="12" class="text-blue-500" />
            <BaseIcon v-else-if="endpoint.mode === '送風'" :path="mdiWeatherWindy" size="12" class="text-teal-500" />
            {{ endpoint.mode }}
          </template>
          <template v-else>
            --
          </template>
        </span>
      </div>
      <!-- 設定溫度 -->
      <div class="flex flex-col min-w-0 border-x border-slate-200/60">
        <span class="text-[12px] font-bold text-slate-400 uppercase tracking-tighter">設定</span>
        <span class="text-md font-bold text-slate-700 mt-0.5 font-mono">
          {{ endpoint.isConnected ? endpoint.setTemp.toFixed(1) : '--' }}<small class="text-[12px] text-slate-400 font-sans ml-0.5">°C</small>
        </span>
      </div>
      <!-- 回風溫度 -->
      <div class="flex flex-col min-w-0">
        <span class="text-[12px] font-bold text-slate-400 uppercase tracking-tighter">回風</span>
        <span class="text-md font-black text-slate-800 mt-0.5 font-mono flex items-center justify-center">
          <BaseIcon :path="mdiThermometer" size="12" class="text-[#2a7eb5]" />
          {{ endpoint.isConnected ? endpoint.returnTemp.toFixed(1) : '--' }}<small class="text-[12px] text-slate-400 font-sans ml-0.5">°C</small>
        </span>
      </div>
    </div>

    <!-- 壓縮機狀態明細 -->
    <div class="space-y-1.5 pt-1">
      <div class="text-[12px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
        <BaseIcon :path="mdiAirConditioner" size="11" />
        壓縮機運行指標
      </div>

      <div 
        v-for="comp in endpoint.compressors" 
        :key="comp.id"
        class="flex items-center justify-between text-xs py-1 px-1.5 bg-slate-50/20 rounded-md border border-slate-100/30"
      >
        <span class="font-bold text-slate-500">壓縮機 {{ comp.id }}</span>
        <div class="flex items-center gap-2">
          <span 
            class="px-1.5 py-0.5 rounded text-[12px] font-bold tracking-wider"
            :class="comp.status === CompressorStatus.ON ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'"
          >
            {{ comp.status }}
          </span>
          <span 
            class="font-mono text-[10px] font-bold flex items-center gap-1.5 shrink-0"
          >
            <span class="text-rose-500 font-extrabold">H:{{ (endpoint.isConnected) ? comp.highPress : '--' }}</span>
            <span class="text-slate-300">|</span>
            <span class="text-blue-500 font-extrabold">L:{{ (endpoint.isConnected) ? comp.lowPress : '--' }}</span>
            <small class="text-[8px] font-sans text-slate-400">kPa</small>
          </span>
        </div>
      </div>
    </div>

    <!-- 底部點位資訊與網址連結提示 -->
    <div class="flex justify-between items-center mt-auto pt-2 border-t border-slate-100/50 text-[10px] text-slate-400">
      <span class="font-mono">{{ endpoint.address }}</span>
      <span 
        @click="goToDetail"
        class="font-bold text-[#2a7eb5] flex items-center gap-0.5 cursor-pointer"
      >
        詳細 <BaseIcon :path="mdiChevronRight" size="12" />
      </span>
    </div>
  </div>
</template>
