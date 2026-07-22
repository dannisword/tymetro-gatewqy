<script setup lang="ts">
import BaseIcon from '@/components/BaseIcon.vue';

defineProps<{
  icon: string;
  iconColorClass: string;
  iconBgClass: string;
  endName?: string;
  label: string;
  value: string | number;
  unit?: string;
  valueColorClass?: string;
}>();
</script>

<template>
  <div class="relative bg-white rounded-2xl mb-3 p-5 pt-6 sm:pt-5 pr-5 sm:pr-8 border border-slate-200/90 shadow-sm flex items-center justify-between gap-4 hover:shadow-md transition-all group overflow-hidden">
    <div class="flex items-center gap-4">
      <div :class="iconBgClass" class="w-12 h-12 rounded-full flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
        <BaseIcon :path="icon" :h="'6'" :w="'6'"  size="32" :class="iconColorClass" />
      </div>
      <div class="flex flex-col gap-0.5">
        <div class="flex items-baseline gap-1">
          <span :class="valueColorClass || 'text-slate-800'" class="text-2xl font-bold tracking-tight">{{ value }}</span>
          <span v-if="unit" class="text-sm font-semibold text-slate-500">{{ unit }}</span>
        </div>
        <span class="text-xs font-bold text-slate-500 tracking-wide">{{ label }}</span>
  
      </div>
    </div>

    <!-- 絕對定位：右上角端點標記 -->
    <div 
      v-if="endName"
      class="absolute top-0 right-0 px-4 py-1 text-xs font-bold tracking-wider z-10 bg-[#2a7eb5] text-white rounded-bl-xl rounded-tr-2xl shadow-xs"
    >
      {{ endName }}
    </div>
  </div>
</template>
