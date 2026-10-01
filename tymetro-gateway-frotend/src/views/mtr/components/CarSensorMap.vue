<script setup lang="ts">
import { ref } from 'vue';
import { useFullscreen } from '@vueuse/core';
import SvgViewer from '@/components/SvgViewer.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { 
  mdiFullscreen, 
  mdiFullscreenExit,
  mdiPlus,
  mdiMinus,
  mdiRestore
} from '@mdi/js';
import type { MapSensorMarker } from '@/utils/types';

interface Props {
  planUrl?: string;
  markers: MapSensorMarker[];
  heightClass?: string;
}

withDefaults(defineProps<Props>(), {
  planUrl: '/images/layout.svg',
  heightClass: 'h-[500px]'
});

const mapContainerRef = ref<HTMLElement | null>(null);
const svgViewerRef = ref<any>(null);
const { isFullscreen, toggle: toggleFullscreen } = useFullscreen(mapContainerRef);
</script>

<template>
  <div 
    ref="mapContainerRef"
    :class="[
      'bg-white transition-all duration-200',
      isFullscreen 
        ? 'fixed inset-0 z-[3000] w-screen h-screen p-4 sm:p-6 flex flex-col overflow-hidden bg-slate-50' 
        : 'border border-slate-200 shadow-sm rounded-2xl p-4 mb-4'
    ]"
  >
    <!-- 頂部標題與控制列 -->
    <div class="flex items-center justify-between mb-4 flex-shrink-0">
      <div class="font-extrabold text-slate-800 text-lg tracking-wide flex items-center gap-2">
        <div class="w-1 h-4 bg-[#2a7eb5] rounded-full"></div>
        車廂感測配置圖面
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-slate-400">
          唯讀模式
        </span>
        <button
          @click="toggleFullscreen"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-[#2a7eb5] hover:border-[#2a7eb5] transition-all text-xs font-bold active:scale-95 shadow-sm"
          :title="isFullscreen ? '結束全螢幕' : '全螢幕顯示'"
        >
          <BaseIcon :path="isFullscreen ? mdiFullscreenExit : mdiFullscreen" size="18" />
          <span>{{ isFullscreen ? '結束全螢幕' : '全螢幕' }}</span>
        </button>
      </div>
    </div>

    <!-- SvgViewer 地圖畫布容器 -->
    <div 
      :class="[
        isFullscreen 
          ? 'flex-1 min-h-0 w-full' 
          : heightClass,
        'border border-slate-200/60 rounded-2xl overflow-hidden relative bg-white transition-all duration-300'
      ]"
    >
      <SvgViewer
        ref="svgViewerRef"
        :src="planUrl"
        :markers="markers"
        :editable="false"
        :zoomable="true"
        :initialScale="0.7"
        :minScale="0.2"
        :maxScale="3.0"
      />

      <!-- 右下角縮放浮動按鈕 -->
      <div class="absolute bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-auto">
        <div class="flex flex-col bg-slate-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-1 shadow-2xl">
          <button 
            @click="svgViewerRef?.zoomIn()" 
            class="w-9 h-9 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" 
            title="放大 (Zoom In)"
          >
            <BaseIcon :path="mdiPlus" size="18" />
          </button>
          <button 
            @click="svgViewerRef?.zoomOut()" 
            class="w-9 h-9 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" 
            title="縮小 (Zoom Out)"
          >
            <BaseIcon :path="mdiMinus" size="18" />
          </button>
          <div class="h-[1px] bg-white/10 mx-1.5 my-0.5"></div>
          <button 
            @click="svgViewerRef?.reset()" 
            class="w-9 h-9 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" 
            title="重設視角 (Reset)"
          >
            <BaseIcon :path="mdiRestore" size="16" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
