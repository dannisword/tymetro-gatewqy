<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { mdiCog, mdiClose } from '@mdi/js';
import BaseIcon from '@/components/BaseIcon.vue';

const props = withDefaults(
  defineProps<{
    src: string;
    editable?: boolean;
    markers?: any[];
    zoomable?: boolean;
    initialScale?: number;
    minScale?: number;
    maxScale?: number;
    autoFit?: boolean;
  }>(),
  {
    editable: false,
    markers: () => [],
    zoomable: true,
    initialScale: undefined,
    minScale: 0.05,
    maxScale: 10,
    autoFit: false
  }
);

const emit = defineEmits<{
  (e: 'update:markers', markers: any[]): void;
  (e: 'add-marker', data: any): void;
  (e: 'delete-marker', id: any): void;
  (e: 'click-marker', marker: any): void;
  (e: 'edit-marker', marker: any): void;
}>();

const containerRef = ref<HTMLElement | null>(null);
const dragMarkerIndex = ref<number | null>(null);
const isDropping = ref(false); 
const dropPos = reactive({ x: 0, y: 0 }); 

const state = reactive({
  scale: props.initialScale !== undefined ? props.initialScale : (props.zoomable ? 0.8 : 1.0),
  x: 0,
  y: 0,
  isDragging: false,
  start: { x: 0, y: 0 },
  lastMouse: { x: 0, y: 0 }
});

const handleMouseDown = (e: MouseEvent) => {
  if (dragMarkerIndex.value !== null || isDropping.value) return;
  userAdjusted = true;
  state.isDragging = true;
  state.start = { x: e.clientX - state.x, y: e.clientY - state.y };
};

const startDraggingMarker = (id: number, e: MouseEvent) => {
  if (!props.editable) return;
  e.stopPropagation();
  e.preventDefault();
  dragMarkerIndex.value = id;
  state.lastMouse = { x: e.clientX, y: e.clientY };
};

const handleMouseMove = (e: MouseEvent) => {
  if (dragMarkerIndex.value !== null && props.markers) {
    const dx = (e.clientX - state.lastMouse.x) / state.scale;
    const dy = (e.clientY - state.lastMouse.y) / state.scale;
    
    const newMarkers = [...props.markers];
    const idx = newMarkers.findIndex(m => m.id === dragMarkerIndex.value);
    
    if (idx !== -1) {
      const target = { ...newMarkers[idx] };
      target.x += dx;
      target.y += dy;
      newMarkers[idx] = target;
      emit('update:markers', newMarkers);
      state.lastMouse = { x: e.clientX, y: e.clientY };
    }
    return;
  }

  if (!state.isDragging) return;
  state.x = Math.round(e.clientX - state.start.x);
  state.y = Math.round(e.clientY - state.start.y);
};

const handleGlobalMouseUp = () => {
  state.isDragging = false;
  dragMarkerIndex.value = null;
};

const getMapCoord = (clientX: number, clientY: number) => {
  if (!containerRef.value) return { x: 0, y: 0 };
  const rect = containerRef.value.getBoundingClientRect();
  const offsetX = clientX - rect.left;
  const offsetY = clientY - rect.top;
  return {
    x: Math.round((offsetX - state.x) / state.scale),
    y: Math.round((offsetY - state.y) / state.scale)
  };
};

const onDragOver = (e: DragEvent) => {
  e.preventDefault();
  isDropping.value = true;
  const coord = getMapCoord(e.clientX, e.clientY);
  dropPos.x = coord.x;
  dropPos.y = coord.y;
};

const onDragLeave = () => {
  isDropping.value = false;
};

const onDrop = (e: DragEvent) => {
  e.preventDefault();
  isDropping.value = false;
  const coord = getMapCoord(e.clientX, e.clientY);

  try {
    const rawData = e.dataTransfer?.getData('text/plain');
    if (rawData) {
      const sensorData = JSON.parse(rawData);
      emit('add-marker', { x: coord.x, y: coord.y, ...sensorData });
      // @ts-ignore
      window.TLSuccess?.(`已放置: ${sensorData.label} (${coord.x}, ${coord.y})`);
    }
  } catch (err) {
    console.error("Drop failed:", err);
  }
};

const handleWheel = (e: WheelEvent) => {
  e.preventDefault();
  if (!props.zoomable) return;
  userAdjusted = true;
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  const newScale = Math.min(Math.max(state.scale * delta, props.minScale), props.maxScale);
  
  if (containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    state.x = Math.round(mouseX - (mouseX - state.x) * (newScale / state.scale));
    state.y = Math.round(mouseY - (mouseY - state.y) * (newScale / state.scale));
    state.scale = newScale;
  }
};

// 依容器大小自動縮放置中，涵蓋底圖與所有標記
let userAdjusted = false;

const fit = () => {
  const container = containerRef.value;
  if (!container) return;
  const cRect = container.getBoundingClientRect();
  if (!cRect.width || !cRect.height) return;

  const els = container.querySelectorAll<HTMLElement>('[data-map-item]');
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  els.forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    // 換算回未縮放的畫布座標
    minX = Math.min(minX, (r.left - cRect.left - state.x) / state.scale);
    minY = Math.min(minY, (r.top - cRect.top - state.y) / state.scale);
    maxX = Math.max(maxX, (r.right - cRect.left - state.x) / state.scale);
    maxY = Math.max(maxY, (r.bottom - cRect.top - state.y) / state.scale);
  });
  if (!isFinite(minX)) return;

  const padding = 24;
  const bw = maxX - minX;
  const bh = maxY - minY;
  const scale = Math.min(
    Math.max(Math.min((cRect.width - padding * 2) / bw, (cRect.height - padding * 2) / bh), props.minScale),
    props.maxScale
  );
  state.scale = scale;
  state.x = Math.round((cRect.width - bw * scale) / 2 - minX * scale);
  state.y = Math.round((cRect.height - bh * scale) / 2 - minY * scale);
};

// 設有點擊動作的標記以橘色外框標示 (點擊會觸發事件)
const hasClickAction = (marker: any) => !!marker.styleConfig?.clickAction && marker.styleConfig.clickAction !== 'none';

const reset = () => {
  userAdjusted = false;
  if (props.autoFit) {
    fit();
    return;
  }
  state.scale = props.initialScale !== undefined ? props.initialScale : (props.zoomable ? 0.8 : 1.0);
  state.x = 0;
  state.y = 0;
};

const zoomCenter = (delta: number) => {
  if (!props.zoomable) return;
  if (!containerRef.value) return;
  userAdjusted = true;
  const rect = containerRef.value.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  const newScale = Math.min(Math.max(state.scale * delta, props.minScale), props.maxScale);
  
  state.x = Math.round(centerX - (centerX - state.x) * (newScale / state.scale));
  state.y = Math.round(centerY - (centerY - state.y) * (newScale / state.scale));
  state.scale = newScale;
  console.log(`Zoom called: delta=${delta}, newScale=${state.scale}`);
};

const autoFitIfIdle = () => {
  if (props.autoFit && !userAdjusted) nextTick(fit);
};

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  window.addEventListener('mouseup', handleGlobalMouseUp);
  if (props.autoFit && containerRef.value) {
    // 容器尺寸改變 (如全螢幕切換) 時重新置中
    resizeObserver = new ResizeObserver(autoFitIfIdle);
    resizeObserver.observe(containerRef.value);
  }
});

// 標記非同步載入後重新整版
watch(() => props.markers.length, autoFitIfIdle);

onUnmounted(() => {
  resizeObserver?.disconnect();
  window.removeEventListener('mouseup', handleGlobalMouseUp);
});

// 暴露接口給父組件
defineExpose({
  zoomIn: () => zoomCenter(1.25),
  zoomOut: () => zoomCenter(0.8),
  reset: () => {
    reset();
    console.log('Map Reset called');
  }
});
</script>

<template>
  <div 
    ref="containerRef"
    class="relative w-full h-full overflow-hidden bg-white select-none transition-none"
    :class="[isDropping ? 'ring-inset ring-4 ring-emerald-500' : '']"
    @wheel="handleWheel"
    @mousedown="handleMouseDown"
    @mousemove="handleMouseMove"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- 背景網格 -->
    <div 
      class="absolute inset-0 opacity-5 pointer-events-none"
      style="background-image: radial-gradient(#000 1px, transparent 1px); background-size: 30px 30px;"
    ></div>

    <!-- 地圖畫布容器 -->
    <div 
      class="absolute left-0 top-0 pointer-events-none origin-top-left"
      :style="{
        transform: `translate3d(${state.x}px, ${state.y}px, 0) scale(${state.scale})`
      }"
    >
      <img 
        :src="src" 
        data-map-item
        @load="autoFitIfIdle"
        class="max-w-none max-h-none block" 
        style="margin: 0; padding: 0; border: none;"
      />

      <!-- 拖拽準星 -->
      <div 
        v-if="isDropping"
        class="absolute border-2 border-emerald-500 rounded-full w-10 h-10 -translate-x-1/2 -translate-y-1/2 pointer-events-none flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.5)]"
        :style="{ left: `${dropPos.x}px`, top: `${dropPos.y}px` }"
      >
        <div class="w-1 h-1 bg-emerald-500 rounded-full"></div>
      </div>

      <!-- 標記圖層 -->
      <div 
        v-for="marker in markers" 
        :key="marker.id"
        data-map-item
        class="absolute pointer-events-auto left-0 top-0"
        :style="{
          transform: `translate3d(${marker.x}px, ${marker.y}px, 0) translate(0, -100%)`,
          zIndex: dragMarkerIndex === marker.id ? 100 : 10
        }"
        @mousedown="startDraggingMarker(marker.id || 0, $event)"
        @click="emit('click-marker', marker)"
      >
        <div 
          :title="[marker.code, marker.label, marker.value].filter(Boolean).join(' | ')"
          class="flex border-2 shadow-2xl rounded-2xl px-3 py-2 min-w-[70px] relative group/marker gap-1 transition-colors"
          :class="[
            editable ? 'cursor-move border-slate-200' : (hasClickAction(marker) ? 'cursor-pointer border-transparent' : 'border-transparent'),
            (marker.styleConfig?.valuePosition === 'top' || marker.valuePosition === 'top') ? 'flex-col-reverse items-center' :
            (marker.styleConfig?.valuePosition === 'left' || marker.valuePosition === 'left') ? 'flex-row-reverse items-center justify-start' :
            (marker.styleConfig?.valuePosition === 'right' || marker.valuePosition === 'right') ? 'flex-row items-center justify-start' :
            'flex-col items-center'
          ]"
          :style="{ 
            borderColor: hasClickAction(marker) ? '#f97316' : marker.color,
            backgroundColor: ((marker.bitValue === 1 || marker.value === '1' || marker.value === 'ON' || marker.value === '正常' || marker.value === '運轉' || marker.value === '啟動') && marker.styleConfig?.onColor) ? marker.styleConfig.onColor :
                             ((marker.bitValue === 0 || marker.value === '0' || marker.value === 'OFF' || marker.value === '異常' || marker.value === '停止' || marker.value === '關閉') && marker.styleConfig?.offColor) ? marker.styleConfig.offColor :
                             '#ffffff'
          }"
        >
          <!-- 設定 / 編輯屬性按鈕 -->
          <div 
            v-if="editable"
            @mousedown.stop
            @click.stop="emit('edit-marker', marker)"
            class="absolute -top-2 -left-2 w-6 h-6 bg-[#2a7eb5] text-white rounded-full opacity-0 group-hover/marker:opacity-100 flex items-center justify-center cursor-pointer hover:bg-[#1f638f] transition-all hover:scale-110 shadow-lg z-20"
            title="編輯標記屬性"
          >
            <BaseIcon :path="mdiCog" size="14" />
          </div>

          <!-- 刪除按鈕 -->
          <div 
            v-if="editable"
            @mousedown.stop
            @click.stop="emit('delete-marker', marker.id)"
            class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover/marker:opacity-100 flex items-center justify-center cursor-pointer hover:bg-red-600 transition-all hover:scale-110 shadow-lg z-20"
            title="刪除標記"
          >
            <BaseIcon :path="mdiClose" size="14" />
          </div>

          <span 
            v-if="marker.label" 
            class="text-lg font-black uppercase tracking-tighter whitespace-nowrap"
            :class="[
              (((marker.bitValue === 1 || marker.value === '1' || marker.value === 'ON' || marker.value === '正常' || marker.value === '運轉' || marker.value === '啟動') && marker.styleConfig?.onColor) ||
               ((marker.bitValue === 0 || marker.value === '0' || marker.value === 'OFF' || marker.value === '異常' || marker.value === '停止' || marker.value === '關閉') && marker.styleConfig?.offColor))
                ? 'text-white' : 'text-slate-800'
            ]"
          >{{ marker.label }}</span>
          <span 
            v-if="marker.styleConfig?.showValue !== false"
            class="font-mono font-black text-lg leading-none whitespace-nowrap"
            :class="[
              (((marker.bitValue === 1 || marker.value === '1' || marker.value === 'ON' || marker.value === '正常' || marker.value === '運轉' || marker.value === '啟動') && marker.styleConfig?.onColor) ||
               ((marker.bitValue === 0 || marker.value === '0' || marker.value === 'OFF' || marker.value === '異常' || marker.value === '停止' || marker.value === '關閉') && marker.styleConfig?.offColor))
                ? 'text-white/90' :
              (marker.bitValue === 1 || marker.value === '1' || marker.value === 'ON' || marker.value === '正常' || marker.value === '運轉') ? 'text-emerald-600 font-black' :
              (marker.bitValue === 0 || marker.value === '0' || marker.value === 'OFF' || marker.value === '異常' || marker.value === '停止') ? 'text-slate-400 font-bold' : 'text-slate-800'
            ]"
          >{{ marker.value }}</span>
        </div>
      </div>
    </div>

    <!-- Debug Info -->
    <div v-if="editable" class="absolute top-6 left-6 z-30 pointer-events-none">
      <div class="bg-slate-900/80 backdrop-blur-md border border-white/10 rounded-full px-4 py-1.5 text-[10px] font-mono text-white/60 shadow-xl">
        SCALE: {{ state.scale.toFixed(2) }} | X: {{ state.x }} | Y: {{ state.y }}
      </div>
    </div>

  </div>
</template>

<style scoped>
* {
  transition: none !important;
}
img {
  -webkit-user-drag: none;
}
</style>
