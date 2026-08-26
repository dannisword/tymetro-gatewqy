<script setup lang="ts">
import SvgViewer from '@/components/SvgViewer.vue';
import type { MapSensorMarker } from '@/utils/types';

interface Props {
  planUrl?: string;
  markers: MapSensorMarker[];
}

withDefaults(defineProps<Props>(), {
  planUrl: '/images/layout.svg'
});
</script>

<template>
  <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 mb-4">
    <div class="flex items-center justify-between mb-4">
      <div class="font-extrabold text-slate-800 text-lg tracking-wide flex items-center gap-2">
        <div class="w-1 h-4 bg-[#2a7eb5] rounded-full"></div>
        車廂感測配置圖面
      </div>
      <span class="text-xs font-semibold text-slate-400">
        唯讀模式
      </span>
    </div>
    <div class="h-[500px] border border-slate-200/60 rounded-2xl overflow-hidden relative bg-white">
      <SvgViewer
        :src="planUrl"
        :markers="markers"
        :editable="false"
        :zoomable="true"
        :initialScale="0.7"
        :minScale="0.5"
        :maxScale="1.2"
      />
    </div>
  </div>
</template>
