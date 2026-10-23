<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import {
  mdiRefresh,
  mdiAlertCircleOutline,
  mdiMagnify,
  mdiChevronDown
} from '@mdi/js';

import AgGridView2 from '@/components/AgGridView2.vue';
import { GridOptions } from 'ag-grid-community';
import { getEquipmentEvents } from '@/utils/api';

const { TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '事件紀錄' }
];

const gridOptions: GridOptions = {
  rowSelection: 'single',
  autoSizeStrategy: {
    type: 'fitGridWidth',
  }
};

const pagination = ref({
  number: 0,
  size: 50,
  totalElements: 0,
  totalPages: 0,
});

const actionLabels: Record<string, { text: string; cls: string }> = {
  TRIGGERED: { text: '觸發', cls: 'bg-rose-50 text-rose-700 border-rose-100' },
  CLEARED: { text: '解除', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
  CHANGED: { text: '變更', cls: 'bg-amber-50 text-amber-700 border-amber-100' },
  RESTORED: { text: '恢復', cls: 'bg-sky-50 text-sky-700 border-sky-100' }
};

const gridColumns = ref([
  { headerName: '發生時間', field: 'triggeredAt', flex: 1.3, minWidth: 180, format: 'datetime' },
  { headerName: '車廂', field: 'carVin', flex: 0.7, minWidth: 80 },
  { headerName: '端點', field: 'endPos', flex: 0.5, minWidth: 60 },
  { headerName: '暫存器', field: 'registerCode', flex: 0.8, minWidth: 90 },
  //{ headerName: 'Bit', field: 'bitIndex', flex: 0.4, minWidth: 50 },
  //{ headerName: '點位', field: 'tagName', flex: 1.2, minWidth: 130 },
  { headerName: '說明', field: 'tagDesc', flex: 1.6, minWidth: 200 },
  { headerName: '類別', field: 'eventType', flex: 0.7, minWidth: 80 },

]);

const events = ref([]);
const loading = ref(false);

// Filters
const filterCarVin = ref('');
const filterEndPos = ref('');
const filterRegister = ref('');
const filterAction = ref('');
const filterStart = ref('');
const filterEnd = ref('');

const fetchEvents = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      order: 'DESC'
    };
    if (filterCarVin.value.trim()) params.carVin = filterCarVin.value.trim();
    if (filterEndPos.value) params.endPos = Number(filterEndPos.value);
    if (filterRegister.value.trim()) params.registerCode = filterRegister.value.trim();
    if (filterAction.value) params.action = filterAction.value;
    if (filterStart.value) params.startTime = filterStart.value;
    if (filterEnd.value) params.endTime = filterEnd.value;

    const res = await getEquipmentEvents(params);
    if (res && res.data) {
      events.value = res.data.source || [];
      const totalCount = res.data.total || 0;
      pagination.value.totalElements = totalCount;
      pagination.value.totalPages = Math.ceil(totalCount / pagination.value.size);
    }
  } catch (error) {
    console.error('Fetch equipment events error:', error);
    TLError('載入事件紀錄失敗');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchEvents);

const handleSearch = () => {
  pagination.value.number = 0;
  fetchEvents();
};

const handleReset = () => {
  filterCarVin.value = '';
  filterEndPos.value = '';
  filterRegister.value = '';
  filterAction.value = '';
  filterStart.value = '';
  filterEnd.value = '';
  handleSearch();
};

const handlePaginationChange = ({ page, pageSize }: { page: number; pageSize: number }) => {
  pagination.value.number = page;
  pagination.value.size = pageSize;
  fetchEvents();
};

const inputCls = 'w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all text-sm';
</script>

<template>
  <div class="w-full pb-20 sm:pb-8">

    <div class="w-full mb-4 sm:mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <div class="w-full max-w-[1600px] mx-auto space-y-4 sm:space-y-6">
      <div class="space-y-4">

        <div class="flex flex-col xl:flex-row justify-between items-stretch xl:items-center gap-3 sm:gap-4 bg-white rounded-xl sm:rounded-2xl p-3 sm:p-4 shadow-xs">
          <h3 class="text-slate-800 font-extrabold text-base sm:text-lg flex items-center gap-2 mb-0 shrink-0">
            <BaseIcon :path="mdiAlertCircleOutline" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            事件紀錄列表
          </h3>

          <div class="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2.5 sm:gap-3 w-full xl:w-auto justify-end">
            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">車廂</label>
              <input v-model="filterCarVin" type="text" placeholder="如 1101" :class="[inputCls, 'sm:w-24']" @keyup.enter="handleSearch" />
            </div>

            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">端點</label>
              <div class="relative flex-1 sm:w-24">
                <select v-model="filterEndPos" :class="[inputCls, 'pr-8 appearance-none cursor-pointer']" @change="handleSearch">
                  <option value="">全部</option>
                  <option value="1">1 端</option>
                  <option value="2">2 端</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">暫存器</label>
              <input v-model="filterRegister" type="text" placeholder="如 D40016" :class="[inputCls, 'sm:w-28']" @keyup.enter="handleSearch" />
            </div>
<!-- 
            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">動作</label>
              <div class="relative flex-1 sm:w-28">
                <select v-model="filterAction" :class="[inputCls, 'pr-8 appearance-none cursor-pointer']" @change="handleSearch">
                  <option value="">全部</option>
                  <option v-for="(a, key) in actionLabels" :key="key" :value="key">{{ a.text }}</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
              </div>
            </div> -->

            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">時間</label>
              <input v-model="filterStart" type="datetime-local" :class="[inputCls, 'sm:w-48']" />
              <span class="text-slate-400">~</span>
              <input v-model="filterEnd" type="datetime-local" :class="[inputCls, 'sm:w-48']" />
            </div>

            <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
              <BaseButton
                @click="handleSearch"
                colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-xs px-4 py-1.5 rounded-lg text-sm font-bold flex-1 sm:flex-initial justify-center"
                :icon="mdiMagnify"
              >
                查詢
              </BaseButton>
              <BaseButton
                @click="handleReset"
                colorClass="bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 shadow-xs px-4 py-1.5 rounded-lg text-sm font-bold flex-1 sm:flex-initial justify-center"
                :icon="mdiRefresh"
              >
                重置
              </BaseButton>
            </div>
          </div>
        </div>

        <div class="h-[calc(100vh-270px)] sm:h-[calc(100vh-220px)] min-h-[360px]">
          <AgGridView2
            :options="gridOptions"
            :columns="gridColumns"
            :records="events"
            :pagination="pagination"
            @pagination-change="handlePaginationChange"
          />
        </div>
      </div>
    </div>

  </div>
</template>
