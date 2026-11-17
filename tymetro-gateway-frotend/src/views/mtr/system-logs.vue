<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { mdiTextBoxSearchOutline, mdiMagnify, mdiDelete, mdiDownload } from '@mdi/js';
import { getSystemLogs, downloadSystemLog } from '@/utils/api';

interface LogItem { seq: number; time: string; level: string; source: string; message: string }

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '即時系統日誌' },
];

const logs = ref<LogItem[]>([]);
const level = ref('INFO');
const keyword = ref('');
const limit = ref(500);
const total = ref(0);
const loading = ref(false);
const error = ref('');
const queriedAt = ref('');
const box = ref<HTMLElement | null>(null);

const levelColor: Record<string, string> = {
  DEBUG: 'text-slate-400',
  INFO: 'text-sky-400',
  SUCCESS: 'text-emerald-400',
  WARNING: 'text-amber-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-500 font-bold',
};

const scrollToBottom = async () => {
  await nextTick();
  if (box.value) box.value.scrollTop = box.value.scrollHeight;
};

// 手動查詢：取最新 limit 筆符合條件的 log
const fetchLogs = async () => {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = await getSystemLogs({
      after: 0,
      level: level.value,
      keyword: keyword.value,
      limit: limit.value,
    });
    if (res?.success && res.data) {
      logs.value = res.data.items as LogItem[];
      total.value = res.data.total ?? logs.value.length;
      queriedAt.value = new Date().toLocaleTimeString();
      error.value = '';
      scrollToBottom();
    } else {
      error.value = res?.message || '取得日誌失敗';
    }
  } catch (e: any) {
    error.value = e?.message || '取得日誌失敗';
  } finally {
    loading.value = false;
  }
};

const downloading = ref(false);
const downloadLog = async () => {
  if (downloading.value) return;
  downloading.value = true;
  try {
    const blob = await downloadSystemLog();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
    a.href = url;
    a.download = `gateway_${ts}.log`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e: any) {
    error.value = e?.message || '下載日誌失敗';
  } finally {
    downloading.value = false;
  }
};

const clearView = () => { logs.value = []; total.value = 0; };

const lineCount = computed(() => logs.value.length);

onMounted(fetchLogs);

const inputCls = 'px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all text-sm';
const btnCls = 'inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 text-sm font-medium hover:bg-slate-50 transition-colors';
</script>

<template>
  <div class="w-full pb-20 sm:pb-8">
    <div class="w-full mb-4 sm:mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <div class="w-full max-w-[1600px] mx-auto space-y-4">
      <div class="flex flex-col xl:flex-row justify-between items-stretch xl:items-center gap-3 bg-white rounded-xl sm:rounded-2xl p-3 sm:p-4 shadow-xs">
        <h3 class="text-slate-800 font-extrabold text-base sm:text-lg flex items-center gap-2 mb-0 shrink-0">
          <BaseIcon :path="mdiTextBoxSearchOutline" w="20" h="20" size="20" class="text-[#2a7eb5]" />
          即時系統日誌
          <span class="text-xs font-normal text-slate-400">顯示 {{ lineCount }} 筆 / 符合 {{ total }} 筆<template v-if="queriedAt"> · 查詢於 {{ queriedAt }}</template></span>
        </h3>

        <div class="flex flex-wrap items-center gap-2.5 justify-end">
          <select v-model="level" :class="inputCls">
            <option value="DEBUG">DEBUG 以上</option>
            <option value="INFO">INFO 以上</option>
            <option value="WARNING">WARNING 以上</option>
            <option value="ERROR">ERROR 以上</option>
          </select>
          <select v-model.number="limit" :class="inputCls">
            <option :value="100">100 筆</option>
            <option :value="200">200 筆</option>
            <option :value="500">500 筆</option>
            <option :value="1000">1000 筆</option>
            <option :value="2000">2000 筆</option>
          </select>
          <input v-model="keyword" :class="inputCls" placeholder="關鍵字" @keyup.enter="fetchLogs" />
          <button :class="btnCls" :disabled="loading" @click="fetchLogs">
            <BaseIcon :path="mdiMagnify" w="16" h="16" size="16" />
            {{ loading ? '查詢中…' : '查詢' }}
          </button>
          <button :class="btnCls" :disabled="downloading" @click="downloadLog">
            <BaseIcon :path="mdiDownload" w="16" h="16" size="16" />
            {{ downloading ? '下載中…' : '下載' }}
          </button>
          <button :class="btnCls" @click="clearView">
            <BaseIcon :path="mdiDelete" w="16" h="16" size="16" />
            清除
          </button>
        </div>
      </div>

      <div v-if="error" class="text-sm text-red-500 px-1">{{ error }}</div>

      <div
        ref="box"
        class="bg-slate-900 rounded-xl shadow-xs p-3 overflow-auto font-mono text-xs leading-5 h-[calc(100vh-280px)] min-h-[320px]"
      >
        <div v-if="!logs.length" class="text-slate-500">無符合的日誌</div>
        <div v-for="l in logs" :key="l.seq" class="whitespace-pre-wrap break-all text-slate-200">
          <span class="text-slate-500">{{ l.time }}</span>
          <span :class="[levelColor[l.level] || 'text-slate-300', 'inline-block w-[4.5rem] ml-2']">{{ l.level }}</span>
          <span class="text-slate-500">{{ l.source }}</span>
          <span> - {{ l.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
