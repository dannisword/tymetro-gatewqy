<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useMtrStore } from '@/store/useMtrStore';
import { storeToRefs } from 'pinia';
import { 
  mdiAirConditioner, 
  mdiThermometer, 
  mdiWeatherWindy, 
  mdiSnowflake,
  mdiHeartPulse,
  mdiServer,
  mdiClockOutline,
  mdiTrendingUp,
  mdiFullscreen
} from '@mdi/js';
import ECLineChart from '@/components/ECLineChart.vue';
import ElDialogCustom from '@/components/ElDialogCustom.vue';

const breadcrumbItems = [
  { label: '首頁', to: '/mtr/home' },
  { label: '車廂狀態監控' }
];

// 模擬資料產生
const generateFakeData = (car: number, end: number) => ({
  id: `${car}-${end}`,
  carName: `第 ${car} 節車廂`,
  endName: `${end}端`,
  compressors: [
    { name: '壓縮機 1', status: 'ON', statusName: '運轉中', statusColor: 'emerald', error: '正常', errorColor: 'emerald', high: 1500, low: 375 },
    { name: '壓縮機 2', status: 'ON', statusName: '運轉中', statusColor: 'emerald', error: '正常', errorColor: 'emerald', high: 1500, low: 375 }
  ],
  returnTemp: '23.8',
  returnTempOffset: '0.0',
  setTemp: '24.5',
  mode: '冷氣'
});

const trainData = ref([1, 2, 3, 4].map(car => ({
  carNo: car,
  carName: `車廂${car}`,
  ends: [1, 2].map(end => generateFakeData(car, end))
})));

const mtrStore = useMtrStore();
const { activeCarId } = storeToRefs(mtrStore);

watch(activeCarId, (val) => {
  console.log(val);
  // 切換 mqtt
});
const currentCar = computed(() => trainData.value.find(c => c.carNo === activeCarId.value));

// 扁平化壓縮機列表，以避免在 tbody 中使用 <template v-for> 造成的 DOM Patch 錯誤
const flattenedCompressors = computed(() => {
  if (!currentCar.value) return [];
  return currentCar.value.ends.flatMap(endData => 
    endData.compressors.map((comp, index) => ({
      ...comp,
      endName: endData.endName,
      endId: endData.id,
      uniqueKey: `${endData.id}-${comp.name}-${index}`
    }))
  );
});

// 趨勢圖數據
const chartXData = ref(['17:00', '17:01', '17:02', '17:03', '17:04', '17:05', '17:06', '17:07', '17:08', '17:09']);

const chartSeriesData = computed(() => {
  const offset = (activeCarId.value - 1) * 0.2;
  return {
    '1端 回風溫度': [23.5, 23.6, 23.8, 23.7, 23.8, 23.9, 23.8, 23.7, 23.8, 23.8].map(v => Number((v + offset).toFixed(1))),
    '2端 回風溫度': [24.1, 24.2, 24.0, 23.9, 24.1, 24.0, 24.2, 24.1, 24.0, 23.9].map(v => Number((v - offset).toFixed(1))),
    '設定溫度': [24.5, 24.5, 24.5, 24.5, 24.5, 24.5, 24.5, 24.5, 24.5, 24.5]
  };
});

const chartColorMap = {
  '1端 回風溫度': '#2a7eb5',
  '2端 回風溫度': '#10b981',
  '設定溫度': '#f59e0b'
};

const isChartDialogVisible = ref(false);

const handleChartDialogClose = (dialogRef: any) => {
  isChartDialogVisible.value = false;
  dialogRef.close = false;
  dialogRef.success = false;
};

onMounted(() => {
 
});

onBeforeUnmount(() => {

});
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    <div class="w-full mb-4">
      <Breadcrumb title="車廂狀態監控" :items="breadcrumbItems" />
    </div>

    <div class="w-full px-4 max-w-[1600px] mx-auto">

      <!-- 當前選中車廂展示 (包含 1端 與 2端) -->
      <div 
        v-if="currentCar" 
        class="flex flex-col gap-5 max-w-6xl mx-auto animate-in fade-in duration-200"
      >
        <!-- 第一大區塊：空調環境與模式參數 -->
        <div class="flex flex-col gap-4">
          <div class="flex items-center justify-between px-2">
            <div class="font-bold text-slate-800 text-lg tracking-wide flex items-center gap-2.5">
              <BaseIcon :path="mdiThermometer" :w="'8'" :h="'8'" size="32" class="text-[#2a7eb5]" />
              空調環境與模式參數
            </div>
            <span class="text-sm font-semibold text-[#2a7eb5] bg-blue-50 border border-blue-100 px-3.5 py-1 rounded-full tracking-wider">
              {{ currentCar.carName }}
            </span>
          </div>

          <!-- 1端 / 2端 分組 -->
          <div 
            v-for="endData in currentCar.ends" 
            :key="endData.id"
            class="flex flex-col gap-3"
          >
            <!-- 端點群組標題 -->
            <div class="text-sm font-bold text-[#2a7eb5] tracking-wider">
              {{ endData.endName }}
            </div>

            <!-- 3 欄 Card Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">

              <!-- 運轉模式 -->
              <div class="flex items-center gap-3 px-4 py-3 bg-slate-50/80 rounded-xl border border-slate-200/60">
                <div class="w-9 h-9 rounded-full bg-[#2a7eb5] flex items-center justify-center shrink-0">
                  <BaseIcon :path="mdiSnowflake" size="24" class="text-white" />
                </div>
                <div class="flex flex-col min-w-0">
                  <span class="text-[11px] font-bold text-slate-400 tracking-wide">運轉模式</span>
                  <span class="text-base font-bold text-[#2a7eb5] truncate">{{ endData.mode }}</span>
                </div>
              </div>

              <!-- 設定溫度 -->
              <div class="flex items-center gap-3 px-4 py-3 bg-slate-50/80 rounded-xl border border-slate-200/60">
                <div class="w-9 h-9 rounded-full bg-[#2a7eb5] flex items-center justify-center shrink-0">
                  <BaseIcon :path="mdiThermometer" size="18" class="text-white" />
                </div>
                <div class="flex flex-col min-w-0">
                  <span class="text-[11px] font-bold text-slate-400 tracking-wide">設定溫度</span>
                  <span class="text-base font-bold text-slate-800">
                    {{ endData.setTemp }}<span class="text-sm font-semibold text-slate-400 ml-0.5">°C</span>
                  </span>
                </div>
              </div>

              <!-- 回風溫度 -->
              <div class="flex items-center gap-3 px-4 py-3 bg-slate-50/80 rounded-xl border border-slate-200/60">
                <div class="w-9 h-9 rounded-full bg-[#2a7eb5] flex items-center justify-center shrink-0" @click="isChartDialogVisible = true">
                  <BaseIcon :path="mdiWeatherWindy" size="18" class="text-white" />
                </div>
                <div class="flex flex-col min-w-0"  >
                  <span class="text-[11px] font-bold text-slate-400 tracking-wide">回風溫度</span>
                  <span class="text-base font-bold text-slate-800">
                    {{ endData.returnTemp }}<span class="text-sm font-semibold text-slate-400 ml-0.5">°C</span>
                  </span>
                </div>
              </div>

            </div>
          </div>
        </div>

        <!-- 溫度趨勢圖區塊 -->
        <!-- 
        <div class="flex flex-col gap-4">
          <div class="flex items-center justify-between px-2">
            <div class="font-bold text-slate-800 text-lg tracking-wide flex items-center gap-2.5">
              <BaseIcon :path="mdiTrendingUp" :w="'8'" :h="'8'" size="32" class="text-[#2a7eb5]" />
              車廂溫度歷史趨勢圖
            </div>
            <button 
              @click="isChartDialogVisible = true"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-[#2a7eb5] bg-blue-50 hover:bg-blue-100/80 border border-blue-200/60 transition-colors shadow-xs"
            >
              <BaseIcon :path="mdiFullscreen" w="w-4" h="h-4" size="16" class="text-[#2a7eb5]" />
              彈窗顯示
            </button>
          </div>
          <div class="bg-white p-4 rounded-xl border border-slate-200/60 shadow-xs">
            <ECLineChart 
              :x="chartXData" 
              :seriesData="chartSeriesData" 
              :colorMap="chartColorMap" 
            />
          </div>
        </div>-->


        <!-- 第二大區塊：壓縮機運轉狀態表 -->
        <div class="flex flex-col gap-4">
          <div class="flex items-center justify-between px-2">
            <div class="font-bold text-slate-800 text-lg tracking-wide flex items-center gap-2.5">
              <BaseIcon :path="mdiAirConditioner" :w="'8'" :h="'8'" size="32" class="text-[#2a7eb5]" />
              壓縮機運轉狀態總表
            </div>
          </div>
          
          <div class="bg-white rounded-xl overflow-x-auto">
            <table class="w-full text-left border-collapse min-w-[650px]">
              <thead>
                <tr class="bg-[#2a7eb5] border-b border-slate-200 text-white text-sm font-bold">
                  <th class="py-3.5 px-4 w-24">端點位置</th>
                  <th class="py-3.5 px-4">設備名稱</th>
                  <th class="py-3.5 px-4">啟停狀態</th>
                  <th class="py-3.5 px-4">異常狀態</th>
                  <th class="py-3.5 px-4 text-right">高壓讀值</th>
                  <th class="py-3.5 px-4 text-right">低壓讀值</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-[14px]">
                <tr 
                  v-for="comp in flattenedCompressors" 
                  :key="comp.uniqueKey"
                  class="hover:bg-slate-50/50 transition-colors"
                >
                  <td class="py-3.5 px-4 font-bold">
                    <span class="px-3 py-1 rounded-md text-sm font-bold shadow-xs border border-[#2a7eb5] bg-[#2a7eb5] text-white inline-block">
                      {{ comp.endName }}
                    </span>
                  </td>
                  <td class="py-3.5 px-4 font-semibold text-slate-800">{{ comp.name }}</td>
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2.5 py-1 rounded-full text-sm font-bold tracking-wider shadow-sm inline-block"
                      :class="comp.status === 'ON' ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600 border border-slate-200'"
                    >
                      {{ comp.statusName }}
                    </span>
                  </td>
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2.5 py-1 rounded-full text-sm font-bold tracking-wider shadow-sm inline-block"
                      :class="comp.error === '正常' ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : 'bg-red-100 text-red-700 border border-red-200'"
                    >
                      {{ comp.error }}
                    </span>
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono font-bold text-red-600">
                    {{ comp.high }} <span class="text-sm font-sans font-normal text-slate-400">KPa</span>
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono font-bold text-blue-600">
                    {{ comp.low }} <span class="text-sm font-sans font-normal text-slate-400">KPa</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>

    <!-- 歷史趨勢圖彈窗 -->
    <ElDialogCustom
      title="歷史趨勢圖"
      :visible="isChartDialogVisible"
      :show-action="false"
      width="75%"
      @on-before-close="handleChartDialogClose"
    >
      <div class="p-2 bg-white rounded-xl">
        <ECLineChart 
          v-if="isChartDialogVisible"
          :x="chartXData" 
          :seriesData="chartSeriesData" 
          :colorMap="chartColorMap" 
        />
      </div>
    </ElDialogCustom>
  </div>
</template>

