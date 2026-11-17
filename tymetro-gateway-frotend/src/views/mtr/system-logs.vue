<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { mdiTextBoxSearchOutline, mdiPause, mdiPlay, mdiDelete, mdiArrowDownBold } from '@mdi/js';
import { getSystemLogs } from '@/utils/api';

interface LogItem { seq: number; time: string; level: string; source: string; message: string }

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '即時系統日誌' },
];

const MAX_LINES = 3000;
const POLL_MS = 1500;

const logs = ref<LogItem[]>([]);
const level = ref('INFO');
const keyword = ref('');
const paused = ref(false);
const autoScroll = ref(true);
const error = ref('');
const box = ref<HTMLElement | null>(null);

let lastSeq = 0;
let timer: ReturnType<typeof setTimeout> | null = null;
let inflight = false;
let stopped = false;

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

const fetchLogs = async () => {
  if (inflight) return;
  inflight = true;
  try {
    const res = await getSystemLogs({
      after: lastSeq,
      level: level.value,
      keyword: keyword.value,
      limit: lastSeq === 0 ? 500 : 1000,
    });
    if (res?.success && res.data) {
      const { items, latest } = res.data as { items: LogItem[]; latest: number };
      // 後端重啟時 seq 會歸零
      if (latest < lastSeq) {
        logs.value = [];
        lastSeq = 0;
        return;
      }
      lastSeq = latest;
      if (items.length) {
        logs.value = logs.value.concat(items).slice(-MAX_LINES);
        if (autoScroll.value) scrollToBottom();
      }
      error.value = '';
    } else {
      error.value = res?.message || '取得日誌失敗';
    }
  } catch (e: any) {
    error.value = e?.message || '取得日誌失敗';
  } finally {
    inflight = false;
  }
};

const loop = async () => {
  if (stopped) return;
  if (!paused.value) await fetchLogs();
  timer = setTimeout(loop, POLL_MS);
};

// 篩選條件改變 → 清空重抓 (以 seq 0 取最新一批)
const reload = () => {
  logs.value = [];
  lastSeq = 0;
  fetchLogs();
};

const clearView = () => { logs.value = []; };

const onScroll = () => {
  const el = box.value;
  if (!el) return;
  autoScroll.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
};

const togglePause = () => { paused.value = !paused.value; };

const lineCount = computed(() => logs.value.length);

onMounted(() => { stopped = false; loop(); });
onBeforeUnmount(() => {
  stopped = true;
  if (timer) clearTimeout(timer);
});

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
          <span class="text-xs font-normal text-slate-400">{{ lineCount }} 行 · {{ paused ? '已暫停' : '更新中' }}</span>
        </h3>

        <div class="flex flex-wrap items-center gap-2.5 justify-end">
          <select v-model="level" :class="inputCls" @change="reload">
            <option value="DEBUG">DEBUG 以上</option>
            <option value="INFO">INFO 以上</option>
            <option value="WARNING">WARNING 以上</option>
            <option value="ERROR">ERROR 以上</option>
          </select>
          <input v-model="keyword" :class="inputCls" placeholder="關鍵字" @keyup.enter="reload" @change="reload" />
          <button :class="btnCls" @click="togglePause">
            <BaseIcon :path="paused ? mdiPlay : mdiPause" w="16" h="16" size="16" />
            {{ paused ? '繼續' : '暫停' }}
          </button>
          <button :class="btnCls" @click="clearView">
            <BaseIcon :path="mdiDelete" w="16" h="16" size="16" />
            清除
          </button>
          <button v-if="!autoScroll" :class="btnCls" @click="autoScroll = true; scrollToBottom()">
            <BaseIcon :path="mdiArrowDownBold" w="16" h="16" size="16" />
            回到最新
          </button>
        </div>
      </div>

      <div v-if="error" class="text-sm text-red-500 px-1">{{ error }}</div>

      <div
        ref="box"
        class="bg-slate-900 rounded-xl shadow-xs p-3 overflow-auto font-mono text-xs leading-5 h-[calc(100vh-280px)] min-h-[320px]"
        @scroll="onScroll"
      >
        <div v-if="!logs.length" class="text-slate-500">尚無日誌</div>
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
