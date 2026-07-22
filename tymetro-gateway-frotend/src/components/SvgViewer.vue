<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';

const props = withDefaults(
  defineProps<{
    src: string;
    editable?: boolean;
    markers?: any[];
    zoomable?: boolean;
    initialScale?: number;
    minScale?: number;
    maxScale?: number;
  }>(),
  {
    editable: false,
    markers: () => [],
    zoomable: true,
    initialScale: undefined,
    minScale: 0.05,
    maxScale: 10
  }
);

const emit = defineEmits<{
  (e: 'update:markers', markers: any[]): void;
  (e: 'add-marker', data: any): void;
  (e: 'delete-marker', id: any): void;
  (e: 'click-marker', marker: any): void;
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

const reset = () => {
  state.scale = props.initialScale !== undefined ? props.initialScale : (props.zoomable ? 0.8 : 1.0);
  state.x = 0;
  state.y = 0;
};

const zoomCenter = (delta: number) => {
  if (!props.zoomable) return;
  if (!containerRef.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  const newScale = Math.min(Math.max(state.scale * delta, props.minScale), props.maxScale);
  
  state.x = Math.round(centerX - (centerX - state.x) * (newScale / state.scale));
  state.y = Math.round(centerY - (centerY - state.y) * (newScale / state.scale));
  state.scale = newScale;
  console.log(`Zoom called: delta=${delta}, newScale=${state.scale}`);
};

onMounted(() => {
  window.addEventListener('mouseup', handleGlobalMouseUp);
});

onUnmounted(() => {
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
        class="absolute pointer-events-auto left-0 top-0"
        :style="{
          transform: `translate3d(${marker.x}px, ${marker.y}px, 0) translate(-50%, -100%)`,
          zIndex: dragMarkerIndex === marker.id ? 100 : 10
        }"
        @mousedown="startDraggingMarker(marker.id || 0, $event)"
        @click="emit('click-marker', marker)"
      >
        <div 
          class="flex flex-col items-center bg-white border-2 shadow-2xl rounded-2xl px-3 py-2 min-w-[70px] relative group/marker"
          :class="[editable ? 'cursor-move border-slate-200' : 'border-transparent']"
          :style="{ borderColor: marker.color }"
        >
          <!-- 刪除按鈕 -->
          <div 
            v-if="editable"
            @click.stop="emit('delete-marker', marker.id)"
            class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover/marker:opacity-100 flex items-center justify-center text-sm cursor-pointer hover:bg-red-600 transition-all hover:scale-110 shadow-lg z-20"
            title="刪除標記"
          >
            ×
          </div>

          <span v-if="marker.label" class="text-lg font-black uppercase tracking-tighter mb-0.5 text-slate-800">{{ marker.label }}</span>
          <span class="font-mono font-black text-slate-800 text-lg leading-none">{{ marker.value }}</span>
        </div>
      </div>
    </div>

    <!-- Debug Info -->
    <div class="absolute top-6 left-6 z-30 pointer-events-none">
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
