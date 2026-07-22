<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import ElDialogCustom from '@/components/ElDialogCustom.vue';
import ECLineChart from '@/components/ECLineChart.vue';
import { getRegisterTrend } from '@/utils/api';
import type { ModbusRegisterRow } from '@/utils/types';

// ─── Props ───────────────────────────────────────────────────────────────────
interface Props {
  visible: boolean;
  register: ModbusRegisterRow | null;
  carNo: number;
  endPos: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void;
}>();

// ─── 時間範圍選項 ─────────────────────────────────────────────────────────────
type RangeKey = '1h' | '6h' | '24h' | '3d' | '7d';

interface RangeOption {
  key: RangeKey;
  label: string;
  hours: number;
}

const rangeOptions: RangeOption[] = [
  { key: '1h',  label: '1 小時',  hours: 1 },
  { key: '6h',  label: '6 小時',  hours: 6 },
  { key: '24h', label: '24 小時', hours: 24 },
  { key: '3d',  label: '3 天',    hours: 72 },
  { key: '7d',  label: '7 天',    hours: 168 },
];

const activeRange = ref<RangeKey>('24h');
const isLoading   = ref(false);
const hasError    = ref(false);

// ─── 圖表數據 ─────────────────────────────────────────────────────────────────
const xLabels    = ref<string[]>([]);
const seriesData = ref<Record<string, number[]>>({});

// ─── 摘要統計 ─────────────────────────────────────────────────────────────────
const stats = computed(() => {
  const values = Object.values(seriesData.value)[0] ?? [];
  if (values.length === 0) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const avg = values.reduce((s, v) => s + v, 0) / values.length;
  return {
    min: min.toFixed(2),
    max: max.toFixed(2),
    avg: avg.toFixed(2),
  };
});

// ─── 對話框標題 ───────────────────────────────────────────────────────────────
const dialogTitle = computed(() => {
  if (!props.register) return '趨勢圖';
  const plcAddr = 40001 + props.register.address;
  const desc = props.register.sensorName || props.register.sensorCode;
  return `趨勢圖 — ${plcAddr} ${desc}`;
});

// ─── ECLineChart 顏色 ────────────────────────────────────────────────────────
const colorMap = computed<Record<string, string>>(() => {
  if (!props.register) return {};
  const desc = props.register.sensorName || props.register.sensorCode;
  return { [desc]: '#3b82f6' };
});

// ─── 載入歷史資料 ─────────────────────────────────────────────────────────────
const loadHistory = async () => {
  if (!props.register || !props.register.id) {
    console.warn('[RegisterTrendModal] register or register.id is null/undefined');
    return;
  }

  isLoading.value = true;
  hasError.value  = false;
  xLabels.value   = [];
  seriesData.value = {};

  const opt = rangeOptions.find(r => r.key === activeRange.value)!;
  const now   = new Date();
  const start = new Date(now.getTime() - opt.hours * 3600 * 1000);

  try {
    const res = await getRegisterTrend(props.register.id, {
      startTime: start.toISOString(),
      endTime:   now.toISOString(),
      limit:     2000,
    });

    if (res && res.success && res.data && Array.isArray(res.data.points) && res.data.points.length > 0) {
      const raw: { timestamp: string; value: string }[] = res.data.points;

      // ── 依時間排序並直接轉換成圖表點 ─────────────────────────────────
      const sortedRaw = [...raw].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      const formattedTimes = sortedRaw.map(item => {
        const dt = new Date(item.timestamp);
        const mm = String(dt.getMonth() + 1).padStart(2, '0');
        const dd = String(dt.getDate()).padStart(2, '0');
        const hh = String(dt.getHours()).padStart(2, '0');
        const min = String(dt.getMinutes()).padStart(2, '0');
        const ss = String(dt.getSeconds()).padStart(2, '0');
        return `${mm}/${dd} ${hh}:${min}:${ss}`;
      });

      const values = sortedRaw.map(item => Number(item.value));

      xLabels.value    = formattedTimes;
      const desc = props.register.sensorName || props.register.sensorCode;
      seriesData.value = { [desc]: values };
    } else {
      // 無資料 — 保留空陣列讓空狀態UI顯示
      xLabels.value    = [];
      seriesData.value = {};
    }
  } catch (e) {
    console.error('[RegisterTrendModal] loadHistory error:', e);
    hasError.value = true;
  } finally {
    isLoading.value = false;
  }
};

// ─── 對話框開啟時自動載入，切換範圍時重新載入 ─────────────────────────────────
watch(
  () => props.visible,
  (val) => {
    if (val) {
      activeRange.value = '24h';
      loadHistory();
    }
  }
);

watch(activeRange, () => {
  if (props.visible) loadHistory();
});

// ─── 關閉對話框 ───────────────────────────────────────────────────────────────
const handleClose = (dialogRef: any) => {
  if (dialogRef.close || dialogRef.success === false || !dialogRef.success) {
    emit('update:visible', false);
  }
};
</script>

<template>
  <ElDialogCustom
    :title="dialogTitle"
    :visible="props.visible"
    width="100%"
    min-height="480px"
    :show-action="false"
    @on-before-close="handleClose"
  >
    <div class="flex flex-col gap-4 py-1">

      <!-- ── 時間範圍篩選 ─────────────────────────────────────────────────── -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-xs font-black text-slate-400 uppercase tracking-widest mr-1 shrink-0">
          時間範圍
        </span>
        <div class="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-0.5">
          <button
            v-for="opt in rangeOptions"
            :key="opt.key"
            @click="activeRange = opt.key"
            :class="[
              'px-3.5 py-1.5 text-sm font-black rounded-lg transition-all duration-200 whitespace-nowrap',
              activeRange === opt.key
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-800 hover:bg-white/70'
            ]"
          >
            {{ opt.label }}
          </button>
        </div>

        <!-- 資料狀態提示 -->
        <span class="text-[11px] font-semibold text-slate-400 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200 shrink-0">
          原始數據
        </span>
      </div>

      <!-- ── 暫存器資訊列 ────────────────────────────────────────────────── -->
      <div class="flex flex-wrap items-center gap-3 text-xs text-slate-500 font-bold bg-slate-50 px-3 py-2 rounded-xl border border-slate-200/60 w-fit">
        <span>PLC 位址: <span class="font-mono text-blue-600 font-black">{{ register ? 40001 + register.address : '--' }}</span></span>
        <span class="text-slate-300">|</span>
        <span>名稱: <span class="text-slate-800 font-extrabold">{{ register?.sensorName ?? register?.sensorCode ?? '--' }}</span></span>
        <template v-if="register?.sensorUnit">
          <span class="text-slate-300">|</span>
          <span>單位: <span class="text-slate-800 font-extrabold">{{ register.sensorUnit }}</span></span>
        </template>
      </div>

      <!-- ── 圖表區域 ────────────────────────────────────────────────────── -->
      <div class="relative rounded-2xl border border-slate-200/80 bg-slate-50/40 overflow-hidden" style="min-height: 300px;">

        <!-- 載入中 overlay -->
        <div
          v-if="isLoading"
          class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-white/80 backdrop-blur-sm z-10 rounded-2xl"
        >
          <div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span class="text-sm font-bold text-slate-500">載入歷史資料中…</span>
        </div>

        <!-- 錯誤狀態 -->
        <div
          v-else-if="hasError"
          class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-rose-500"
        >
          <svg class="w-10 h-10 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span class="text-sm font-bold">讀取失敗，請稍後再試</span>
        </div>

        <!-- 無資料空狀態 -->
        <div
          v-else-if="!isLoading && xLabels.length === 0"
          class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-slate-400"
        >
          <svg class="w-12 h-12 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
          </svg>
          <span class="text-sm font-bold">此時間範圍內無歷史資料</span>
        </div>

        <!-- 折線圖 -->
        <ECLineChart
          v-if="!isLoading && !hasError && xLabels.length > 0"
          :x="xLabels"
          :series-data="seriesData"
          :color-map="colorMap"
        />
      </div>

      <!-- ── 摘要統計 ────────────────────────────────────────────────────── -->
      <div v-if="stats" class="grid grid-cols-3 gap-3">
        <div class="flex flex-col items-center py-3 px-4 bg-blue-50/70 rounded-xl border border-blue-100">
          <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">最小值</span>
          <span class="text-xl font-black font-mono text-blue-700 tracking-tight">{{ stats.min }}</span>
          <span class="text-[10px] text-blue-400 font-bold mt-0.5">{{ register?.sensorUnit ?? '' }}</span>
        </div>
        <div class="flex flex-col items-center py-3 px-4 bg-emerald-50/70 rounded-xl border border-emerald-100">
          <span class="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1">平均值</span>
          <span class="text-xl font-black font-mono text-emerald-700 tracking-tight">{{ stats.avg }}</span>
          <span class="text-[10px] text-emerald-400 font-bold mt-0.5">{{ register?.sensorUnit ?? '' }}</span>
        </div>
        <div class="flex flex-col items-center py-3 px-4 bg-rose-50/70 rounded-xl border border-rose-100">
          <span class="text-[10px] font-black text-rose-400 uppercase tracking-widest mb-1">最大值</span>
          <span class="text-xl font-black font-mono text-rose-700 tracking-tight">{{ stats.max }}</span>
          <span class="text-[10px] text-rose-400 font-bold mt-0.5">{{ register?.sensorUnit ?? '' }}</span>
        </div>
      </div>

    </div>
  </ElDialogCustom>
</template>

<style scoped>
.border-3 {
  border-width: 3px;
}
</style>
