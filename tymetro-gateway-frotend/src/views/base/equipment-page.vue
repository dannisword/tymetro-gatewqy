<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRoute } from "vue-router";
import SvgViewer from "@/components/SvgViewer.vue";
import httpOperations from "@/utils/http-operations";
import { 
  mdiFormatListBulleted, 
  mdiRefresh, 
  mdiClose, 
  mdiCursorMove, 
  mdiCheck, 
  mdiPlus, 
  mdiMinus, 
  mdiRestore 
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import { getBitLabel } from "@/utils/mtrHelper";

const route = useRoute();
const isEdit = ref(false);
const sidebarOpen = ref(false);
const planUrl = "/images/layout.svg";
const equipmentInfo = ref<any>(null);
const equipmentId = computed(() => route.params.equipmentId as any);
const endPos = computed(() => route.params.endPos as any);
const svgViewerRef = ref<any>(null);

// ... fetchData, handleSaveConfig, handleDragStart, onMarkerAdd 保持不變 ...
const bitLabelsMap = ref<Record<string, Record<number, string>>>({});

const fetchBitLabels = async () => {
  try {
    const res = await httpOperations.get('/api/v1/sensor-bit-labels');
    if (res && res.success) {
      const list = res.data || [];
      const mapping: Record<string, Record<number, string>> = {};
      list.forEach((item: any) => {
        const code = item.sensorCode.toUpperCase();
        if (!mapping[code]) {
          mapping[code] = {};
        }
        mapping[code][item.bitIndex] = item.label;
      });
      bitLabelsMap.value = mapping;
    }
  } catch (err) {
    console.error("Fetch bit labels error:", err);
  }
};

const getBitLabelLocal = (sensorCode: string, bitIndex: number) => {
  const code = sensorCode.toUpperCase();
  if (bitLabelsMap.value[code] && bitLabelsMap.value[code][bitIndex] !== undefined) {
    return bitLabelsMap.value[code][bitIndex];
  }
  return getBitLabel(sensorCode, bitIndex);
};

const fetchData = async () => {
  if (!equipmentId.value) return;
  try {
    loading.value = true;
    await fetchBitLabels();
    
    const sensorRes = await httpOperations.get(`/api/v1/sensors/equipment/${equipmentId.value}`);
    if (sensorRes.success) {
      equipmentInfo.value = sensorRes.data.equipment;
      allSensors.value = (sensorRes.data.sensors || []).map((reg: any) => {
        const isTemp = reg.sensorUnit === '°C' || (reg.sensorName && reg.sensorName.includes('溫度'));
        return {
          ...reg,
          sensorTypeName: isTemp ? '溫度' : '其他'
        };
      });
    }

    const mapRes = await httpOperations.get(`/api/v1/sensor-maps/template/HVAC_STANDARD`);
    if (mapRes.success && mapRes.data) {
      const mapData = mapRes.data || [];
      sensors.value = mapData.map((m: any) => {
        const isBitmap = m.bitIndex !== null && m.bitIndex !== undefined;
        const matched = allSensors.value.find(as => as.sensorCode === m.sensorCode);
        let resolvedVal = "0.0";
        if (matched) {
          if (matched.dataType === 'bitmap' && isBitmap) {
            const bitVal = matched.sensorValue.charAt(15 - m.bitIndex) || '0';
            resolvedVal = bitVal === '1' ? 'ON' : 'OFF';
          } else {
            resolvedVal = matched.sensorValue;
          }
        }
        return {
          id: isBitmap ? `${m.sensorCode}_bit${m.bitIndex}` : m.sensorCode,
          x: m.x,
          y: m.y,
          label: m.label || (isBitmap ? getBitLabelLocal(m.sensorCode, m.bitIndex) : m.sensorCode),
          value: resolvedVal,
          code: m.sensorCode,
          bitIndex: m.bitIndex,
          color: m.color || (m.markerType === 'circle' ? '#10b981' : '#3b82f6'),
          type: m.markerType || 'rect'
        };
      });
    }
  } catch (error) {
    console.error("Fetch failed:", error);
  } finally {
    loading.value = false;
  }
};

const handleSaveConfig = async () => {
  if (!equipmentId.value) return;

  try {
    const payload = sensors.value.map(s => ({
      templateCode: "HVAC_STANDARD",
      sensorCode: s.code,
      bitIndex: s.bitIndex !== undefined ? s.bitIndex : null,
      x: s.x,
      y: s.y,
      markerType: s.type || 'rect',
      color: s.color,
      label: s.label,
      isActive: true
    }));

    const res = await httpOperations.post(`/api/v1/sensor-maps/batch/HVAC_STANDARD`, payload);
    if (res.success) {
      isEdit.value = false;
      // @ts-ignore
      window.TLSuccess?.("配置儲存成功");
    }
  } catch (error) {
    console.error("Save failed:", error);
  }
};

const handleDragStart = (sensor: any, bitIndex: number | null, e: DragEvent) => {
  if (!e.dataTransfer) return;
  const isBitmap = bitIndex !== null;
  const dragData = {
    id: isBitmap ? `${sensor.sensorCode}_bit${bitIndex}` : sensor.sensorCode,
    code: sensor.sensorCode,
    bitIndex: bitIndex,
    label: isBitmap ? getBitLabelLocal(sensor.sensorCode, bitIndex) : sensor.sensorName,
    value: isBitmap ? '0' : sensor.sensorValue,
    color: sensor.sensorTypeName === '溫度' ? '#10b981' : '#3b82f6',
    type: sensor.sensorTypeName === '溫度' ? 'circle' : 'rect'
  };
  e.dataTransfer.setData('text/plain', JSON.stringify(dragData));
  e.dataTransfer.dropEffect = 'copy';
};

const onMarkerAdd = (data: any) => {
  const exists = sensors.value.some(s => s.id === data.id);
  if (exists) {
    sensors.value = sensors.value.map(s => s.id === data.id ? { ...s, x: data.x, y: data.y } : s);
  } else {
    sensors.value = [...sensors.value, data];
  }
};

const onMarkerDelete = (id: any) => {
  sensors.value = sensors.value.filter(s => s.id !== id);
  if (selectedMarker.value && selectedMarker.value.id === id) {
    selectedMarker.value = null;
  }
};

const selectedMarker = ref<any>(null);

const handleMarkerClick = (marker: any) => {
  if (!isEdit.value) return;
  selectedMarker.value = { ...marker };
};

const handleSaveMarkerEdit = () => {
  if (!selectedMarker.value) return;
  sensors.value = sensors.value.map(s => s.id === selectedMarker.value.id ? { ...selectedMarker.value } : s);
  selectedMarker.value = null;
  // @ts-ignore
  window.TLSuccess?.("標記屬性套用成功（請記得儲存配置以永久存檔）");
};

onMounted(() => fetchData());

const sensors = ref<any[]>([]); 
const allSensors = ref<any[]>([]); 
const loading = ref(false);

watch(() => allSensors.value, (newAll) => {
  sensors.value = sensors.value.map(s => {
    const matched = newAll.find(as => as.sensorCode === s.code);
    if (matched) {
      if (matched.dataType === 'bitmap' && s.bitIndex !== null && s.bitIndex !== undefined) {
        const bitVal = matched.sensorValue.charAt(15 - s.bitIndex);
        return { ...s, value: bitVal === '1' ? 'ON' : 'OFF' };
      }
      return { ...s, value: matched.sensorValue };
    }
    return s;
  });
}, { deep: true });
</script>

<template>
  <div class="p-3 h-[calc(100vh-125px)] w-full flex flex-col overflow-hidden relative bg-slate-50/50">
    <!-- Header: 保持極簡 -->
    <div class="flex items-center justify-between mb-4 flex-shrink-0 px-2">
      <div class="flex flex-col">
        <div class="flex items-baseline gap-3">
          <h1 class="text-2xl font-black text-slate-800 tracking-tight leading-none">感測器配置</h1>
          <span class="text-xs text-slate-400 font-bold uppercase tracking-[0.2em] leading-none">{{ equipmentInfo?.carNo }} - {{ endPos }}端</span>
        </div>
        <div class="flex items-center gap-2 mt-1">
          <div class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
          <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">{{ equipmentInfo?.equipmentName }}</span>
        </div>
      </div>
    </div>

    <!-- Map Container -->
    <div class="flex-1 min-h-0 relative rounded-[2.5rem] overflow-hidden border border-slate-200 shadow-2xl bg-white group">
      <SvgViewer
        ref="svgViewerRef"
        :src="planUrl"
        v-model:markers="sensors"
        :editable="isEdit"
        @add-marker="onMarkerAdd"
        @delete-marker="onMarkerDelete"
        @click-marker="handleMarkerClick"
      />

      <!-- 右下角整合工具欄 (純圖示) -->
      <div class="absolute bottom-8 right-8 z-50 flex flex-col gap-2 pointer-events-auto">
        <!-- 功能控制組 -->
        <div class="flex flex-col bg-slate-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-1 shadow-2xl">
          <!-- 開啟清單 -->
          <button 
            @click="sidebarOpen = true" 
            class="w-12 h-12 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90"
            title="開啟感測器清單"
          >
            <BaseIcon :path="mdiFormatListBulleted" size="22" class="text-emerald-400" />
          </button>
          
          <div class="h-[1px] bg-white/10 mx-2 my-0.5"></div>

          <!-- 位置調整開關 -->
          <button
            @click="isEdit ? handleSaveConfig() : (isEdit = true)"
            :class="[
              'w-12 h-12 flex items-center justify-center rounded-xl transition-all active:scale-90',
              isEdit ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.5)]' : 'hover:bg-white/10 text-white'
            ]"
            :title="isEdit ? '儲存配置' : '調整標記位置'"
          >
            <BaseIcon :path="isEdit ? mdiCheck : mdiCursorMove" size="22" />
          </button>
        </div>

        <!-- 縮放控制組 -->
        <div class="flex flex-col bg-slate-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-1 shadow-2xl">
          <button @click="svgViewerRef?.zoomIn()" class="w-12 h-12 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" title="放大">
            <BaseIcon :path="mdiPlus" size="22" />
          </button>
          <button @click="svgViewerRef?.zoomOut()" class="w-12 h-12 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" title="縮小">
            <BaseIcon :path="mdiMinus" size="22" />
          </button>
          <div class="h-[1px] bg-white/10 mx-2 my-0.5"></div>
          <button @click="svgViewerRef?.reset()" class="w-12 h-12 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" title="重設視角">
            <BaseIcon :path="mdiRestore" size="18" />
          </button>
        </div>
      </div>
    </div>

    <!-- Custom Drawer (替代 el-drawer 以避免拖拽攔截) -->
    <transition name="drawer">
      <div v-if="sidebarOpen" class="fixed top-0 right-0 h-full w-[380px] bg-white shadow-[-20px_0_60px_rgba(0,0,0,0.15)] z-[2000] flex flex-col border-l border-slate-100">
        <!-- Drawer Header -->
        <div class="flex items-center justify-between p-6 bg-slate-50/50 border-b border-slate-100">
          <div>
            <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Equipment Sensors</div>
            <div class="text-lg font-black text-slate-800">{{ equipmentInfo?.carNo || '設備' }} 模板清單</div>
          </div>
          <button @click="sidebarOpen = false" class="p-2 hover:bg-slate-200 rounded-full transition-colors">
            <BaseIcon :path="mdiClose" size="20" class="text-slate-500" />
          </button>
        </div>

        <!-- Sensor List -->
        <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3 custom-scrollbar">
          <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-slate-300">
            <div class="animate-spin mb-4"><BaseIcon :path="mdiRefresh" size="32" /></div>
            <span class="text-xs font-bold uppercase tracking-widest">Loading Sensors...</span>
          </div>
          
          <div 
            v-for="sensor in allSensors" 
            :key="sensor.id"
          >
            <!-- 1. 當非 bitmap 型別時，整張卡片都可以拖曳 -->
            <div 
              v-if="sensor.dataType !== 'bitmap'"
              draggable="true"
              @dragstart="handleDragStart(sensor, null, $event)"
              class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-emerald-400 transition-all cursor-grab active:cursor-grabbing group border-l-4 mb-3"
              :style="{ borderLeftColor: sensor.sensorTypeName === '溫度' ? '#10b981' : '#3b82f6' }"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-black text-slate-700 truncate pr-2">{{ sensor.sensorName }}</span>
                <div class="px-2 py-0.5 bg-slate-100 rounded text-[9px] font-black text-slate-400 uppercase">{{ sensor.sensorTypeName }}</div>
              </div>
              <div class="flex items-baseline gap-1 font-mono font-black text-slate-800">
                <span class="text-2xl">{{ sensor.sensorValue }}</span>
                <span class="text-xs text-slate-400 uppercase">{{ sensor.sensorUnit }}</span>
              </div>
            </div>

            <!-- 2. 當為 bitmap 型別時，展示 16 個 Bit 可供各別拖曳 -->
            <div 
              v-else
              class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm border-l-4 border-l-purple-500 mb-3"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-black text-slate-700 truncate pr-2">{{ sensor.sensorName }} (Bitmap)</span>
                <div class="px-2 py-0.5 bg-purple-100 text-purple-600 rounded text-[9px] font-black uppercase">位元遮罩</div>
              </div>
              
              <div class="flex flex-col gap-1.5 mt-2 max-h-[220px] overflow-y-auto pr-1">
                <div 
                  v-for="bit in 16" 
                  :key="bit - 1"
                  draggable="true"
                  @dragstart="handleDragStart(sensor, bit - 1, $event)"
                  class="bg-slate-50 hover:bg-purple-50/50 border border-slate-100 rounded-lg p-2 flex items-center justify-between text-xs cursor-grab active:cursor-grabbing hover:border-purple-200 transition-all select-none"
                  :title="`拖曳此位元 (${getBitLabelLocal(sensor.sensorCode, bit - 1)})`"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="font-mono font-black text-[8px] bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded">B{{ bit - 1 }}</span>
                    <span class="font-bold text-slate-700 truncate text-[11px]">{{ getBitLabelLocal(sensor.sensorCode, bit - 1) }}</span>
                  </div>
                  <span class="font-mono font-black text-[11px]" :class="[sensor.sensorValue.charAt(16 - bit) === '1' ? 'text-emerald-500' : 'text-slate-400']">
                    {{ sensor.sensorValue.charAt(16 - bit) || '0' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer Info -->
        <div class="p-4 bg-slate-50 border-t border-slate-100">
          <p class="text-[10px] text-slate-400 font-bold text-center uppercase tracking-tighter">
            請將感測器卡片直接拖拽至左側地圖區域
          </p>
        </div>
      </div>
    </transition>

    <!-- 編輯標記側邊欄抽屜 (當處於編輯狀態且有選中標記時) -->
    <transition name="drawer">
      <div v-if="isEdit && selectedMarker" class="fixed top-0 right-0 h-full w-[350px] bg-white shadow-2xl z-[2001] flex flex-col border-l border-slate-100">
        <!-- Drawer Header -->
        <div class="flex items-center justify-between p-5 bg-slate-50/50 border-b border-slate-100">
          <div>
            <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Edit Marker</div>
            <div class="text-base font-black text-slate-800">編輯標記屬性</div>
          </div>
          <button @click="selectedMarker = null" class="p-2 hover:bg-slate-200 rounded-full transition-colors">
            <BaseIcon :path="mdiClose" size="20" class="text-slate-500" />
          </button>
        </div>

        <!-- Form Content -->
        <div class="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider">點位代碼</label>
            <input 
              type="text" 
              :value="selectedMarker.code + (selectedMarker.bitIndex !== null && selectedMarker.bitIndex !== undefined ? ` (Bit ${selectedMarker.bitIndex})` : '')" 
              disabled 
              class="w-full px-3 py-2 rounded-xl border border-slate-100 bg-slate-50 text-slate-500 font-mono text-sm outline-none"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider">顯示標籤名稱</label>
            <input 
              type="text" 
              v-model="selectedMarker.label" 
              placeholder="請輸入顯示標籤"
              class="w-full px-3 py-2 rounded-xl border border-slate-200 focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none text-sm font-semibold transition-all"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider">標記顏色 (Hex)</label>
            <div class="flex gap-2 items-center">
              <input 
                type="color" 
                v-model="selectedMarker.color" 
                class="w-8 h-8 rounded-lg border-0 cursor-pointer overflow-hidden bg-transparent"
              />
              <input 
                type="text" 
                v-model="selectedMarker.color" 
                placeholder="#3b82f6"
                class="flex-1 px-3 py-2 rounded-xl border border-slate-200 focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none text-sm font-mono transition-all"
              />
            </div>
          </div>
          
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider">標記類型</label>
            <div class="grid grid-cols-2 gap-2">
              <button 
                @click="selectedMarker.type = 'circle'" 
                class="py-2 text-xs font-black rounded-xl border transition-all"
                :class="[selectedMarker.type === 'circle' ? 'bg-slate-900 border-slate-900 text-white' : 'border-slate-200 hover:bg-slate-50 text-slate-600']"
              >
                圓形 (Circle)
              </button>
              <button 
                @click="selectedMarker.type = 'rect'" 
                class="py-2 text-xs font-black rounded-xl border transition-all"
                :class="[selectedMarker.type === 'rect' ? 'bg-slate-900 border-slate-900 text-white' : 'border-slate-200 hover:bg-slate-50 text-slate-600']"
              >
                矩形 (Rect)
              </button>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="p-4 bg-slate-50 border-t border-slate-100 grid grid-cols-2 gap-2">
          <button 
            @click="selectedMarker = null"
            class="py-2.5 rounded-xl border border-slate-200 text-xs font-black text-slate-600 hover:bg-slate-100 transition-all active:scale-95"
          >
            取消
          </button>
          <button 
            @click="handleSaveMarkerEdit"
            class="py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-black transition-all active:scale-95 shadow-[0_4px_12px_rgba(16,185,129,0.2)]"
          >
            確定套用
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* 自定義抽屜動畫 */
.drawer-enter-active, .drawer-leave-active {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-enter-from, .drawer-leave-to {
  transform: translateX(100%);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  @apply bg-slate-200 rounded-full;
}
</style>
