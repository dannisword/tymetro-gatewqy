<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import SvgViewer from "@/components/SvgViewer.vue";
import httpOperations from "@/utils/http-operations";
import { useMtrStore } from "@/store/useMtrStore";
import { getBitLabel } from "@/utils/mtrHelper";
import { 
  mdiRefresh, 
  mdiClose, 
  mdiCloudDownload,
  mdiPlus,
  mdiMinus,
  mdiRestore
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import BaseButton from "@/components/BaseButton.vue";
import Breadcrumb from '@/components/Breadcrumb.vue';
import { downloadSensorMaps } from "@/utils/api";
import { useAlert } from "@/composables/TLAlter";

const mtrStore = useMtrStore();
const { TLSuccess, TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '感測器圖面配置' }
];

const planUrl = "/images/layout.svg";
const svgViewerRef = ref<any>(null);
const sensors = ref<any[]>([]); 
const allSensors = ref<any[]>([]); 
const loading = ref(false);

const isDownloadModalOpen = ref(false);
const downloadTemplateCode = ref('HVAC_STANDARD');
const downloadLoading = ref(false);

const openDownloadDialog = () => {
  downloadTemplateCode.value = 'HVAC_STANDARD';
  isDownloadModalOpen.value = true;
};

const handleDownload = async () => {
  const code = (downloadTemplateCode.value || '').trim() || 'HVAC_STANDARD';
  downloadLoading.value = true;
  try {
    const res = await downloadSensorMaps(code);
    if (res && res.success) {
      TLSuccess(res.message || `成功自中心端下載樣板 [${code}] 圖面配置！`);
      isDownloadModalOpen.value = false;
      await fetchData();
    } else {
      TLError(res?.message || '下載感測器圖面配置失敗');
    }
  } catch (error: any) {
    console.error("Download failed:", error);
    TLError("下載失敗: " + (error?.message || error));
  } finally {
    downloadLoading.value = false;
  }
};

// 數值對照 (key: sensorCode)：(暫存器值 & bitMask) === matchValue 時顯示 text
interface ValueLabel { bitMask: number; matchValue: number; text: string }
const valueLabelMap = ref<Record<string, ValueLabel[]>>({});
// 位元名稱 (key: sensorCode → bitIndex → 名稱)，來自 text 為 NULL 的位元名稱列
const bitLabelsMap = ref<Record<string, Record<number, string>>>({});

const fetchValueLabels = async () => {
  try {
    const res = await httpOperations.get('/api/v1/sensor-value-labels');
    if (res.success && Array.isArray(res.data)) {
      const valueMap: Record<string, ValueLabel[]> = {};
      const bitMap: Record<string, Record<number, string>> = {};
      res.data.forEach((v: any) => {
        const code = String(v.sensorCode).toUpperCase();
        if (v.text == null || v.matchValue == null) {
          if (v.label) (bitMap[code] ||= {})[Math.log2(v.bitMask)] = v.label;
          return;
        }
        (valueMap[v.sensorCode] ||= []).push({ bitMask: v.bitMask, matchValue: v.matchValue, text: v.text });
      });
      valueLabelMap.value = valueMap;
      bitLabelsMap.value = bitMap;
    }
  } catch (error) {
    console.error("Fetch value labels failed:", error);
  }
};

const findValueText = (code: string, raw: number, predicate: (mask: number) => boolean): string | undefined =>
  valueLabelMap.value[code]?.find(v => predicate(v.bitMask) && (raw & v.bitMask) === v.matchValue)?.text;

const getBitLabelLocal = (sensorCode: string, bitIndex: number) =>
  bitLabelsMap.value[sensorCode.toUpperCase()]?.[bitIndex] ?? getBitLabel(sensorCode, bitIndex);

const resolveMarkerValue = (matched: any, code: string, bitIndex?: number | null) => {
  if (!matched) return { value: '0.0', bitValue: undefined };
  // 1. Bit 標記
  if (matched.dataType === 'bitmap' && bitIndex !== null && bitIndex !== undefined) {
    const rawStr = String(matched.sensorValue ?? '');
    let bitVal = 0;
    if (rawStr.length >= 16 && /^[01]+$/.test(rawStr)) {
      bitVal = rawStr.charAt(15 - bitIndex) === '1' ? 1 : 0;
    } else {
      const intVal = Number(matched.sensorValue) || 0;
      bitVal = (intVal & (1 << bitIndex)) !== 0 ? 1 : 0;
    }
    const bitMask = 1 << bitIndex;
    const customText = findValueText(code, bitVal ? bitMask : 0, mask => mask === bitMask);
    return { value: customText || (bitVal === 1 ? 'ON' : 'OFF'), bitValue: bitVal };
  }
  // 2. 多位元組合判定 (例如主控制模式)
  const comboText = findValueText(code, Number(matched.sensorValue) || 0, mask => (mask & (mask - 1)) !== 0);
  if (comboText) return { value: comboText, bitValue: undefined };
  // 3. 一般數值 (套用縮放比例 scale)
  const scale = matched.scale !== undefined && matched.scale !== null ? Number(matched.scale) : 1.0;
  let val: any = matched.sensorValue ?? '0.0';
  if (scale !== 1.0) {
    val = String((Number(val) * scale).toFixed(1));
  } else if (matched.sensorUnit === '°C' && Number(val) > 100) {
    val = String((Number(val) / 10).toFixed(1));
  }
  return { value: String(val), bitValue: undefined };
};

const fetchData = async () => {
  try {
    loading.value = true;
    
    // 獲取 Modbus 即時值暫存器清單作為感測器來源 (增加 pageSize 以涵蓋所有即時暫存器)
    const registerRes = await httpOperations.get('/api/v1/sensors/by-group', { registerGroup: 'realtime' });
    if (registerRes && registerRes.success) {
      const list = registerRes.data.source || [];
      allSensors.value = list.map((reg: any) => {
        const isTemp = reg.sensorUnit === '°C' || (reg.sensorName && reg.sensorName.includes('溫度'));
        return {
          id: reg.id,
          sensorCode: reg.sensorCode, // 例如 D40201
          sensorName: reg.sensorName || reg.sensorCode,
          sensorValue: reg.sensorValue ?? '0.0',
          scale: reg.scale !== undefined && reg.scale !== null ? Number(reg.scale) : 1.0,
          sensorUnit: reg.sensorUnit || '',
          sensorTypeName: isTemp ? '溫度' : '其他',
          dataType: reg.dataType || 'int16'
        };
      });
    }

    await fetchValueLabels();

    const mapRes = await httpOperations.get('/api/v1/sensor-maps/template/HVAC_STANDARD');
    if (mapRes.success && mapRes.data) {
      const mapData = mapRes.data || [];
      sensors.value = mapData.map((m: any) => {
        const isBitmap = m.bitIndex !== null && m.bitIndex !== undefined;
        const matched = allSensors.value.find(as => as.sensorCode === m.sensorCode);
        const { value, bitValue } = resolveMarkerValue(matched, m.sensorCode, m.bitIndex);

        return {
          id: isBitmap ? `${m.sensorCode}_bit${m.bitIndex}` : m.sensorCode,
          x: m.x,
          y: m.y,
          label: m.label || (isBitmap ? getBitLabelLocal(m.sensorCode, m.bitIndex) : m.sensorCode),
          value,
          bitValue,
          code: m.sensorCode,
          bitIndex: m.bitIndex,
          color: m.color || (m.markerType === 'circle' ? '#10b981' : '#3b82f6'),
          type: m.markerType || 'rect',
          styleConfig: m.styleConfig || { valuePosition: 'bottom' }
        };
      });
    }
  } catch (error) {
    console.error("Fetch failed:", error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
});

watch(() => allSensors.value, (newAll) => {
  sensors.value = sensors.value.map(s => {
    const matched = newAll.find(as => as.sensorCode === s.code);
    if (!matched) return s;
    return { ...s, ...resolveMarkerValue(matched, s.code, s.bitIndex) };
  });
}, { deep: true });
</script>

<template>
  <div class="w-full pb-12 sm:pb-4 flex flex-col h-[calc(100vh-100px)]">
    <!-- Breadcrumb -->
    <div class="w-full mb-2 flex-shrink-0">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <!-- Header -->
    <div class="flex justify-between items-center mb-3 flex-shrink-0 px-1">
      <h3 class="text-slate-800 font-extrabold text-lg flex items-center gap-2 mb-0">
        <div class="w-1 h-4 bg-[#2a7eb5] rounded-full"></div>
        感測器圖面配置
      </h3>
      <div class="flex items-center gap-2">
        <BaseButton
          @click="openDownloadDialog"
          color-class="bg-[#2a7eb5] hover:bg-[#206796] text-white shadow-sm text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 transition-all active:scale-95"
          :icon="mdiCloudDownload"
        >
          下載 tymetro 設定
        </BaseButton>
      </div>
    </div>

    <!-- Map Container -->
    <div class="flex-1 min-h-0 relative rounded-2xl overflow-hidden border border-slate-200 shadow-lg bg-white group">
      <div v-if="loading" class="absolute inset-0 z-10 bg-white/60 backdrop-blur-[1px] flex items-center justify-center">
        <div class="flex flex-col items-center gap-2 text-slate-500">
          <BaseIcon :path="mdiRefresh" size="28" class="animate-spin text-[#2a7eb5]" />
          <span class="text-xs font-bold tracking-wider">載入圖面配置中...</span>
        </div>
      </div>

      <SvgViewer
        ref="svgViewerRef"
        :src="planUrl"
        v-model:markers="sensors"
        :editable="false"
        :zoomable="true"
        :initial-scale="0.8"
      />

      <!-- 右下角縮放控制工具欄 -->
      <div class="absolute bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-auto">
        <div class="flex flex-col bg-slate-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-1 shadow-2xl">
          <button 
            @click="svgViewerRef?.zoomIn()" 
            class="w-10 h-10 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" 
            title="放大 (Zoom In)"
          >
            <BaseIcon :path="mdiPlus" size="20" />
          </button>
          <button 
            @click="svgViewerRef?.zoomOut()" 
            class="w-10 h-10 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" 
            title="縮小 (Zoom Out)"
          >
            <BaseIcon :path="mdiMinus" size="20" />
          </button>
          <div class="h-[1px] bg-white/10 mx-2 my-0.5"></div>
          <button 
            @click="svgViewerRef?.reset()" 
            class="w-10 h-10 flex items-center justify-center hover:bg-white/10 text-white rounded-xl transition-all active:scale-90" 
            title="重設視角 (Reset)"
          >
            <BaseIcon :path="mdiRestore" size="18" />
          </button>
        </div>
      </div>
    </div>

    <!-- 下載樣板彈窗 Modal -->
    <transition name="fade">
      <div v-if="isDownloadModalOpen" class="fixed inset-0 z-[2500] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
        <div class="bg-white rounded-2xl shadow-2xl border border-slate-100 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
          <!-- Modal Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-xl bg-[#2a7eb5]/10 text-[#2a7eb5] flex items-center justify-center">
                <BaseIcon :path="mdiCloudDownload" size="20" />
              </div>
              <div>
                <h4 class="text-sm font-black text-slate-800 mb-0">下載感測器圖面配置</h4>
                <p class="text-[11px] text-slate-400 mb-0">自 tymetro 中心端同步樣板標記點位</p>
              </div>
            </div>
            <button 
              @click="isDownloadModalOpen = false" 
              class="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <BaseIcon :path="mdiClose" size="18" />
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-6 flex flex-col gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-black text-slate-700">樣板代碼 (Template Code)</label>
              <input 
                type="text" 
                v-model="downloadTemplateCode" 
                placeholder="例如: HVAC_STANDARD"
                @keyup.enter="handleDownload"
                class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none text-sm font-semibold transition-all"
              />
              <span class="text-[11px] text-slate-400 font-medium">預設下載：<code class="text-[#2a7eb5] bg-sky-50 px-1.5 py-0.5 rounded font-mono font-bold">HVAC_STANDARD</code></span>
            </div>

            <div class="p-3 bg-amber-50/70 border border-amber-200/60 rounded-xl text-xs text-amber-800 leading-relaxed">
              下載後將自動覆蓋本機 SQLite 的配置資料，並立即重新套用載入標記點位座標與屬性。
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="px-6 py-4 bg-slate-50/50 border-t border-slate-100 flex justify-end gap-2.5">
            <button 
              @click="isDownloadModalOpen = false" 
              class="px-4 py-2 rounded-xl border border-slate-200 text-xs font-black text-slate-600 hover:bg-slate-100 transition-all active:scale-95"
            >
              取消
            </button>
            <button 
              @click="handleDownload" 
              :disabled="downloadLoading"
              class="px-5 py-2 rounded-xl bg-[#2a7eb5] hover:bg-[#206796] text-white text-xs font-black transition-all active:scale-95 shadow-md flex items-center gap-1.5 disabled:opacity-50"
            >
              <BaseIcon v-if="downloadLoading" :path="mdiRefresh" size="16" class="animate-spin" />
              <span>{{ downloadLoading ? '下載中...' : '確認下載' }}</span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
