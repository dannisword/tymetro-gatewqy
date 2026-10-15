<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import {
  mdiRefresh,
  mdiHistory,
  mdiMagnify,
  mdiChevronDown
} from '@mdi/js';

import AgGridView2 from '@/components/AgGridView2.vue';
import { GridOptions } from 'ag-grid-community';
import { getModbusRecords, getModbusRegisters } from '@/utils/api';

const { TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '歷史資料查詢' }
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

const gridColumns = ref([
  {
    headerName: '時間',
    field: 'timestamp',
    flex: 1.5,
    minWidth: 160,
    format: 'datetime'
  },
  {
    headerName: '車廂編號',
    field: 'carVin',
    flex: 1.5,
    minWidth: 150
  },
    {
    headerName: '端點',
    field: 'endPos',
    flex: 1.5,
    minWidth: 150
  },
  {
    headerName: '讀取值',
    field: 'value',
    flex: 1.2,
    minWidth: 110,
    cellRenderer: (p: any) => {
      return `<span class="font-mono font-bold text-slate-800">${p.value}</span>`;
    }
  },
  {
    headerName: '暫存器 ID',
    field: 'registerId',
    flex: 1.0,
    minWidth: 110
  }
]);

const records = ref([]);
const loading = ref(false);

// Filters
const filterRegisterId = ref<number | string>('');

const MAX_RANGE_MS = 2 * 24 * 60 * 60 * 1000; // 查詢區間上限 2 天

// datetime-local 格式 (本地時間) YYYY-MM-DDTHH:mm:ss
const toLocalInput = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
// 預設為今日 00:00:00 ~ 23:59:59
const defaultRange = () => {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date();
  end.setHours(23, 59, 59, 0);
  return { start: toLocalInput(start), end: toLocalInput(end) };
};
const filterStartTime = ref(defaultRange().start);
const filterEndTime = ref(defaultRange().end);

// 後端 recordedAt 為 UTC (無時區)，本地時間轉成 UTC 字串送出
const toUtcParam = (local: string) => new Date(local).toISOString().slice(0, 19);

const validateRange = (): boolean => {
  if (!filterStartTime.value || !filterEndTime.value) {
    TLError('請選擇起訖時間');
    return false;
  }
  const diff = new Date(filterEndTime.value).getTime() - new Date(filterStartTime.value).getTime();
  if (diff < 0) {
    TLError('結束時間不可早於開始時間');
    return false;
  }
  if (diff > MAX_RANGE_MS) {
    TLError('查詢區間最多 2 天');
    return false;
  }
  return true;
};
const registersOptions = ref<any[]>([]);
const filterCarVin = ref('');
const filterEndPos = ref<number | string>('');
// 車廂編號選項：由暫存器清單的 carVin 去重排序
const carVinOptions = computed(() =>
  Array.from(new Set(registersOptions.value.map((r: any) => r.carVin).filter(Boolean)))
    .map(String)
    .sort()
);

const fetchRegisters = async () => {
  try {
    const res = await getModbusRegisters({ pageSize: 1000 });
    if (res && res.data) {
      registersOptions.value = (res.data.source || []).map((r: any) => ({
        ...r,
        name: r.sensorCode,
        description: r.sensorName
      }));
    }
  } catch (error) {
    console.error('Fetch registers failed:', error);
  }
};

const fetchRecords = async () => {
  if (!validateRange()) return;
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      propertyName: 'recordedAt',
      order: 'DESC',
      startTime: toUtcParam(filterStartTime.value),
      endTime: toUtcParam(filterEndTime.value)
    };
    if (filterRegisterId.value !== '') {
      params.sensorCode = filterRegisterId.value;
    }
    if (filterCarVin.value !== '') {
      params.carVin = filterCarVin.value;
    }
    if (filterEndPos.value !== '') {
      params.endPos = filterEndPos.value;
    }

    const res = await getModbusRecords(params);
    if (res && res.data) {
      records.value = (res.data.source || []).map((item: any) => ({
        ...item,
        timestamp: item.recordedAt,
        name: item.sensorCode,
        value: item.sensorValue,
        registerId: item.sensorCode
      }));
      const totalCount = res.data.total || 0;
      pagination.value.totalElements = totalCount;
      pagination.value.totalPages = Math.ceil(totalCount / pagination.value.size);
    }
  } catch (error) {
    console.error('Fetch modbus records error:', error);
    TLError('載入歷史紀錄失敗');
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await fetchRegisters();
  await fetchRecords();
});

const handleSearch = () => {
  pagination.value.number = 0;
  fetchRecords();
};

const handleReset = () => {
  filterRegisterId.value = '';
  filterCarVin.value = '';
  filterEndPos.value = '';
  filterStartTime.value = defaultRange().start;
  filterEndTime.value = defaultRange().end;
  pagination.value.number = 0;
  fetchRecords();
};

const handlePaginationChange = ({ page, pageSize }: { page: number; pageSize: number }) => {
  pagination.value.number = page;
  pagination.value.size = pageSize;
  fetchRecords();
};
</script>

<template>
  <div class="w-full pb-20 sm:pb-8">
    
    <!-- Breadcrumb -->
    <div class="w-full mb-4 sm:mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <!-- 內容區 -->
    <div class="w-full max-w-[1600px] mx-auto space-y-4 sm:space-y-6">

      <!-- 資料表與操作 -->
      <div class="space-y-4">
        
        <!-- 表格頂端標題與搜尋條件一排 -->
        <div class="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-3 sm:gap-4 bg-white rounded-xl sm:rounded-2xl p-3 sm:p-4 shadow-xs">
          <!-- 表格頂端標題 -->
          <h3 class="text-slate-800 font-extrabold text-base sm:text-lg flex items-center gap-2 mb-0 shrink-0">
            <BaseIcon :path="mdiHistory" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            歷史資料查詢
          </h3>

          <!-- 搜尋與按鈕 -->
          <div class="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2.5 sm:gap-3 w-full md:w-auto justify-end">
            <!-- 起訖時間 (區間最多 2 天)，獨佔第一排 -->
            <div class="flex items-center gap-2 w-full sm:justify-end sm:basis-full">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">起訖時間</label>
              <input
                v-model="filterStartTime"
                type="datetime-local"
                step="1"
                :max="filterEndTime"
                class="min-w-0 px-2 py-1.5 rounded-lg border border-slate-200 text-slate-700 text-sm focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white"
              />
              <span class="text-slate-400">~</span>
              <input
                v-model="filterEndTime"
                type="datetime-local"
                step="1"
                :min="filterStartTime"
                class="min-w-0 px-2 py-1.5 rounded-lg border border-slate-200 text-slate-700 text-sm focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white"
              />
            </div>

            <!-- 車廂編號過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">車廂編號</label>
              <div class="relative flex-1 sm:w-36 min-w-0">
                <select
                  v-model="filterCarVin"
                  class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm truncate cursor-pointer"
                  @change="handleSearch"
                >
                  <option value="">全部車廂</option>
                  <option v-for="vin in carVinOptions" :key="vin" :value="vin">{{ vin }}</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
              </div>
            </div>

            <!-- 端點過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">端點</label>
              <div class="relative flex-1 sm:w-28 min-w-0">
                <select
                  v-model="filterEndPos"
                  class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm truncate cursor-pointer"
                  @change="handleSearch"
                >
                  <option value="">全部端點</option>
                  <option :value="1">1 端</option>
                  <option :value="2">2 端</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
              </div>
            </div>

            <!-- 暫存器過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto flex-1 min-w-0">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">暫存器</label>
              <div class="relative flex-1 sm:w-64 min-w-0">
                <select 
                  v-model="filterRegisterId"
                  class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm truncate cursor-pointer"
                  @change="handleSearch"
                >
                  <option value="">全部暫存器</option>
                  <option 
                    v-for="reg in registersOptions" 
                    :key="reg.id" 
                    :value="reg.sensorCode"
                  >
                    {{ reg.name }} ({{ reg.description || '無描述' }})
                  </option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
              </div>
            </div>
            
            <!-- 操作按鈕 -->
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

        <!-- 數據表格 -->
        <div class="h-[calc(100vh-520px)] sm:h-[calc(100vh-290px)] min-h-[360px]">
          <AgGridView2
            :options="gridOptions"
            :columns="gridColumns"
            :records="records"
            :pagination="pagination"
            @pagination-change="handlePaginationChange"
          />
        </div>
      </div>

    </div>

  </div>
</template>
