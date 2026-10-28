<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import {
  mdiRefresh,
  mdiClipboardListOutline,
  mdiMagnify,
  mdiClose,
  mdiChevronDown
} from '@mdi/js';

import AgGridView2 from '@/components/AgGridView2.vue';
import { GridOptions } from 'ag-grid-community';
import { getSettingLogs } from '@/utils/api';

const { TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '設定紀錄' }
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
    field: 'recordedAt',
    flex: 1.2,
    maxWidth: 180,
    format: 'datetime'
  },
  {
    headerName: '設定項目',
    field: 'settingType',
    flex: 1.2,
    minWidth: 160
  },
  {
    headerName: '設定值',
    field: 'value',
    flex: 0.8,
    maxWidth: 140
  },
  {
    headerName: '狀態',
    field: 'status',
    flex: 0.7,
    maxWidth: 80,
    cellRenderer: (p: any) => {
      const status = String(p.value || '').toLowerCase();
      if (status === 'acked') {
        return `<span class="px-2 py-0.5 rounded text-xs font-bold bg-amber-50 text-amber-700 border border-amber-100">處理中</span>`;
      }
      if (status === 'success' || !status) {
        return `<span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">成功</span>`;
      }
      return `<span class="px-2 py-0.5 rounded text-xs font-bold bg-rose-50 text-rose-700 border border-rose-100">失敗</span>`;
    }
  },
  {
    headerName: '操作人',
    field: 'operator',
    flex: 0.9,
    maxWidth: 120
  },
  {
    headerName: '失敗原因',
    field: 'errorMessage',
    valueGetter: (p: any) => p.data?.errorMessage || p.data?.detail || '',
    flex: 1.6,
    minWidth: 200,
    wrapText: true,
    autoHeight: true
  },
  // {
  //   headerName: 'IP 位址',
  //   field: 'ipAddress',
  //   flex: 1.0,
  //   minWidth: 110
  // }
]);

const logs = ref([]);
const total = ref(0);
const loading = ref(false);

// Filters
const filterSettingType = ref('');
const filterStatus = ref('');
const filterOperator = ref('');

const fetchLogs = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      propertyName: 'recordedAt',
      order: 'DESC'
    };
    if (filterSettingType.value.trim()) {
      params.settingType = filterSettingType.value.trim();
    }
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    if (filterOperator.value.trim()) {
      params.operator = filterOperator.value.trim();
    }

    const res = await getSettingLogs(params);
    if (res && res.data) {
      logs.value = res.data.source || [];
      const totalCount = res.data.total || 0;
      total.value = totalCount;
      pagination.value.totalElements = totalCount;
      pagination.value.totalPages = Math.ceil(totalCount / pagination.value.size);
    }
  } catch (error) {
    console.error('Fetch setting logs error:', error);
    TLError('載入設定紀錄失敗');
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await fetchLogs();
});

const handleSearch = () => {
  pagination.value.number = 0;
  fetchLogs();
};

const handleClearOperator = () => {
  filterOperator.value = '';
  handleSearch();
};

const handleReset = () => {
  filterSettingType.value = '';
  filterStatus.value = '';
  filterOperator.value = '';
  pagination.value.number = 0;
  fetchLogs();
};

const handlePaginationChange = ({ page, pageSize }: { page: number; pageSize: number }) => {
  pagination.value.number = page;
  pagination.value.size = pageSize;
  fetchLogs();
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
        <div class="flex flex-col xl:flex-row justify-between items-stretch xl:items-center gap-3 sm:gap-4 bg-white rounded-xl sm:rounded-2xl p-3 sm:p-4 shadow-xs">
          <!-- 表格頂端標題 -->
          <h3 class="text-slate-800 font-extrabold text-base sm:text-lg flex items-center gap-2 mb-0 shrink-0">
            <BaseIcon :path="mdiClipboardListOutline" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            設定紀錄列表
          </h3>

          <!-- 搜尋與按鈕 -->
          <div class="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2.5 sm:gap-3 w-full xl:w-auto justify-end">
            <!-- 設定項目過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto flex-1 min-w-0">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">設定項目</label>
              <div class="relative flex-1 sm:w-44 min-w-0">
                <input 
                  v-model="filterSettingType"
                  type="text"
                  placeholder="輸入設定項目關鍵字"
                  class="w-full pl-3 pr-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all text-sm"
                  @keyup.enter="handleSearch"
                />
              </div>
            </div>

            <!-- 狀態過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto flex-1 min-w-0">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">狀態</label>
              <div class="relative flex-1 sm:w-28 min-w-0">
                <select 
                  v-model="filterStatus"
                  class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm truncate cursor-pointer"
                  @change="handleSearch"
                >
                  <option value="">全部</option>
                  <option value="ACKED">處理中</option>
                  <option value="SUCCESS">成功</option>
                  <option value="FAILED">失敗</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
              </div>
            </div>

            <!-- 操作人過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto flex-1 min-w-0">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">操作人</label>
              <div class="relative flex-1 sm:w-44 min-w-0">
                <input 
                  v-model="filterOperator"
                  type="text"
                  placeholder="輸入操作人關鍵字"
                  class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all text-sm"
                  @keyup.enter="handleSearch"
                />
                <button
                  v-if="filterOperator"
                  @click="handleClearOperator"
                  type="button"
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  title="清除"
                >
                  <BaseIcon :path="mdiClose" w="14" h="14" size="14" />
                </button>
              </div>
            </div>
            
            <!-- 按鈕群組 -->
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
        <div class="h-[calc(100vh-270px)] sm:h-[calc(100vh-220px)] min-h-[360px]">
          <AgGridView2
            :options="gridOptions"
            :columns="gridColumns"
            :records="logs"
            :pagination="pagination"
            @pagination-change="handlePaginationChange"
          />
        </div>
      </div>

    </div>

  </div>
</template>
