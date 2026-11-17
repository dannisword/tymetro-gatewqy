<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseSwitch from '@/components/BaseSwitch.vue';
import { mdiFileDocumentOutline, mdiDownload, mdiContentCopy, mdiClose, mdiMagnify } from '@mdi/js';
import { getSystemLogs, getLogDownloadTicket } from '@/utils/api';
import { useAlert } from '@/composables/TLAlter';

interface LogItem { seq: number; time: string; level: string; source: string; message: string }

const { TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '即時系統日誌' },
];

const MAX_LINES = 3000;
const POLL_MS = 2000;

const logs = ref<LogItem[]>([]);
const total = ref(0);
const level = ref('');
const keyword = ref('');
const lines = ref(100);
const autoRefresh = ref(false);
const wrapLines = ref(true);
const showTimestamps = ref(true);
const loading = ref(false);
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const downloadDate = ref(today());
const downloading = ref(false);
const error = ref('');
const queriedAt = ref('');
const selected = ref<Set<number>>(new Set());
const box = ref<HTMLElement | null>(null);

let lastSeq = 0;
let timer: ReturnType<typeof setTimeout> | null = null;
let stopped = false;
let atBottom = true;

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

const onScroll = () => {
  const el = box.value;
  if (el) atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
};

// incremental=true：只抓 lastSeq 之後的新 log 並附加；否則重抓最新 lines 筆
const fetchLogs = async (incremental = false) => {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = await getSystemLogs({
      after: incremental ? lastSeq : 0,
      level: level.value,
      keyword: keyword.value,
      limit: lines.value,
    });
    if (res?.success && res.data) {
      const items = res.data.items as LogItem[];
      const latest = res.data.latest as number;
      if (incremental && latest >= lastSeq) {
        if (items.length) {
          logs.value = logs.value.concat(items).slice(-MAX_LINES);
          total.value += items.length;
          if (atBottom) scrollToBottom();
        }
      } else {
        logs.value = items;
        total.value = res.data.total ?? items.length;
        selected.value = new Set();
        scrollToBottom();
      }
      lastSeq = latest;
      queriedAt.value = new Date().toLocaleTimeString();
      error.value = '';
    } else {
      error.value = res?.message || '取得日誌失敗';
    }
  } catch (e: any) {
    error.value = e?.message || '取得日誌失敗';
  } finally {
    loading.value = false;
  }
};

const loop = async () => {
  if (stopped || !autoRefresh.value) return;
  await fetchLogs(true);
  timer = setTimeout(loop, POLL_MS);
};

const stopLoop = () => {
  if (timer) { clearTimeout(timer); timer = null; }
};

watch(autoRefresh, (on) => {
  stopLoop();
  if (on) { atBottom = true; loop(); }
});

const reload = () => {
  stopLoop();
  fetchLogs(false).then(() => { if (autoRefresh.value) timer = setTimeout(loop, POLL_MS); });
};

const lineText = (l: LogItem) =>
  `${showTimestamps.value ? l.time + ' ' : ''}${l.level.padEnd(8)} ${l.source} - ${l.message}`;

const toggleSelect = (seq: number) => {
  const s = new Set(selected.value);
  s.has(seq) ? s.delete(seq) : s.add(seq);
  selected.value = s;
};

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
};

const copyAll = () => copyText(logs.value.map(lineText).join('\n'));
const copySelected = () =>
  copyText(logs.value.filter((l) => selected.value.has(l.seq)).map(lineText).join('\n'));
const unselect = () => { selected.value = new Set(); };

const downloadLog = async () => {
  if (downloading.value) return;
  downloading.value = true;
  try {
    const res = await getLogDownloadTicket();
    const ticket = res?.data?.ticket;
    if (!ticket) throw new Error('取得下載票證失敗');
    // 直接以網址下載，由瀏覽器原生處理 (不經 blob)
    const base = (import.meta.env.VITE_BASE_API || '/').replace(/\/$/, '');
    const a = document.createElement('a');
    a.href = `${base}/api/v1/logs/download?ticket=${encodeURIComponent(ticket)}${downloadDate.value ? `&date=${downloadDate.value}` : ''}`;
    a.download = downloadDate.value ? `gateway_${downloadDate.value}.log` : 'gateway.log';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (e: any) {
    TLError(e?.message || '下載日誌失敗');
  } finally {
    downloading.value = false;
  }
};

const selectedCount = computed(() => selected.value.size);

onMounted(() => { stopped = false; fetchLogs(false); });
onBeforeUnmount(() => { stopped = true; stopLoop(); });

const inputCls = 'w-full px-3 py-2 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all text-sm';
const btnCls = 'inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 text-sm font-medium hover:bg-slate-50 transition-colors disabled:opacity-50';
const labelCls = 'block mb-1 text-xs font-bold text-slate-500';
</script>

<template>
  <div class="w-full pb-20 sm:pb-8">
    <div class="w-full mb-4 sm:mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <div class="w-full max-w-[1600px] mx-auto space-y-4">
      <!-- 設定面板 -->
      <div class="bg-white rounded-xl sm:rounded-2xl p-4 shadow-xs space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h3 class="text-slate-800 font-extrabold text-base sm:text-lg flex items-center gap-2 mb-0">
            <span class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
              <BaseIcon :path="mdiFileDocumentOutline" w="18" h="18" size="18" class="text-[#2a7eb5]" />
            </span>
            日誌檢視設定
          </h3>
          <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
            <label class="flex items-center gap-2 text-sm font-bold text-slate-700">
              自動更新 <BaseSwitch v-model="autoRefresh" />
            </label>
            <label class="flex items-center gap-2 text-sm font-bold text-slate-700">
              自動換行 <BaseSwitch v-model="wrapLines" />
            </label>
            <label class="flex items-center gap-2 text-sm font-bold text-slate-700">
              顯示時間 <BaseSwitch v-model="showTimestamps" />
            </label>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[10rem_1fr_8rem_auto] gap-3 items-end">
          <div>
            <label :class="labelCls">等級</label>
            <select v-model="level" :class="inputCls" @change="reload">
              <option value="">全部</option>
              <option value="INFO">INFO 以上</option>
              <option value="WARNING">WARNING 以上</option>
              <option value="ERROR">ERROR 以上</option>
            </select>
          </div>
          <div>
            <label :class="labelCls">搜尋</label>
            <input v-model="keyword" :class="inputCls" placeholder="關鍵字…" @keyup.enter="reload" @change="reload" />
          </div>
          <div>
            <label :class="labelCls">筆數</label>
            <input v-model.number="lines" type="number" min="1" max="2000" :class="inputCls" @keyup.enter="reload" @change="reload" />
          </div>
          <button :class="[btnCls, 'h-[38px] px-5 !bg-[#2a7eb5] !text-white !border-[#2a7eb5] hover:!bg-[#236a99]']" :disabled="loading" @click="reload">
            <BaseIcon :path="mdiMagnify" w="16" h="16" size="16" /> {{ loading ? '查詢中…' : '查詢' }}
          </button>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
          <div class="text-xs text-slate-400">
            顯示 {{ logs.length }} 筆 / 符合 {{ total }} 筆<template v-if="selectedCount"> · 已選取 {{ selectedCount }} 行</template><template v-if="queriedAt"> · 更新於 {{ queriedAt }}</template>
            <span v-if="error" class="text-red-500 ml-2">{{ error }}</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <input v-model="downloadDate" type="date" :max="today()" title="下載日期 (留空＝目前檔案)" class="px-2 py-1.5 rounded-lg border border-slate-200 text-slate-700 text-sm bg-white outline-none focus:border-[#2a7eb5]" />
            <button :class="btnCls" :disabled="downloading" @click="downloadLog">
              <BaseIcon :path="mdiDownload" w="16" h="16" size="16" /> {{ downloading ? '下載中…' : '下載日誌' }}
            </button>
            <button :class="btnCls" @click="copyAll">
              <BaseIcon :path="mdiContentCopy" w="16" h="16" size="16" /> 複製
            </button>
            <button :class="btnCls" :disabled="!selectedCount" @click="copySelected">
              <BaseIcon :path="mdiContentCopy" w="16" h="16" size="16" /> 複製選取行
            </button>
            <button :class="btnCls" :disabled="!selectedCount" @click="unselect">
              <BaseIcon :path="mdiClose" w="16" h="16" size="16" /> 取消選取
            </button>
          </div>
        </div>
      </div>

      <!-- 日誌區 -->
      <div
        ref="box"
        class="bg-slate-900 rounded-xl shadow-xs py-2 overflow-auto font-mono text-xs leading-5 h-[calc(100vh-380px)] min-h-[320px]"
        @scroll="onScroll"
      >
        <div v-if="!logs.length" class="text-slate-500 px-3">無符合的日誌</div>
        <div
          v-for="l in logs"
          :key="l.seq"
          :class="[
            'px-3 cursor-pointer text-slate-200 hover:bg-slate-800',
            wrapLines ? 'whitespace-pre-wrap break-all' : 'whitespace-pre w-max min-w-full',
            selected.has(l.seq) ? 'bg-slate-700 hover:bg-slate-700' : '',
          ]"
          @click="toggleSelect(l.seq)"
        >
          <span v-if="showTimestamps" class="text-slate-500">{{ l.time }} </span>
          <span :class="[levelColor[l.level] || 'text-slate-300', 'inline-block w-[4.5rem]']">{{ l.level }}</span>
          <span class="text-slate-500">{{ l.source }}</span>
          <span> - {{ l.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
