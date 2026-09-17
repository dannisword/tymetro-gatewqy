<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import {
  mdiRefresh,
  mdiShieldCheckOutline,
  mdiMagnify,
  mdiClose,
  mdiChevronDown
} from '@mdi/js';

import AgGridView2 from '@/components/AgGridView2.vue';
import { GridOptions } from 'ag-grid-community';
import { getAuditLogs, getEnums } from '@/utils/api';

const { TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '審計日誌' }
];

const categoryOptions = ref<{ value: string; label: string }[]>([]);
const categoryMap = ref<Record<string, string>>({});

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
    flex: 1.2,
    minWidth: 160,
    format: 'datetime'
  },
  {
    headerName: '審計類別',
    field: 'auditCategory',
    flex: 0.9,
    minWidth: 90,
    cellRenderer: (p: any) => {
      const label = categoryMap.value[p.value] || p.value || '';
      return `<span class="px-2 py-0.5 rounded text-xs font-bold bg-blue-50 text-blue-700 border border-blue-100">${label}</span>`;
    }
  },
  {
    headerName: '動作',
    field: 'action',
    flex: 1.2,
    minWidth: 140
  },
  {
    headerName: '狀態',
    field: 'status',
    flex: 0.7,
    minWidth: 70,
    cellRenderer: (p: any) => {
      const isSuccess = p.value === 'success';
      return isSuccess
        ? `<span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">成功</span>`
        : `<span class="px-2 py-0.5 rounded text-xs font-bold bg-rose-50 text-rose-700 border border-rose-100">失敗</span>`;
    }
  },
  {
    headerName: '操作人',
    field: 'operator',
    flex: 0.9,
    minWidth: 120
  },
  {
    headerName: 'IP 位址',
    field: 'ipAddress',
    flex: 1.0,
    minWidth: 110
  },
  {
    headerName: '詳細資訊',
    field: 'detail',
    flex: 2.2,
    minWidth: 220
  }
]);

const logs = ref([]);
const total = ref(0);
const loading = ref(false);

// Filters
const filterCategory = ref('');
const filterStatus = ref('');
const filterOperator = ref('');

const fetchLogs = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      propertyName: 'timestamp',
      order: 'DESC'
    };
    if (filterCategory.value) {
      params.auditCategory = filterCategory.value;
    }
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    if (filterOperator.value.trim()) {
      params.operator = filterOperator.value.trim();
    }

    const res = await getAuditLogs(params);
    if (res && res.data) {
      logs.value = res.data.source || [];
      const totalCount = res.data.total || 0;
      total.value = totalCount;
      pagination.value.totalElements = totalCount;
      pagination.value.totalPages = Math.ceil(totalCount / pagination.value.size);
    }
  } catch (error) {
    console.error('Fetch audit logs error:', error);
    TLError('載入審計日誌失敗');
  } finally {
    loading.value = false;
  }
};

const loadEnums = async () => {
  try {
    const enumsRes = await getEnums();
    if (enumsRes?.success && enumsRes.data) {
      if (enumsRes.data.auditCategory) {
        categoryOptions.value = enumsRes.data.auditCategory;
      }
      if (enumsRes.data.categoryMap) {
        categoryMap.value = enumsRes.data.categoryMap;
      }
    }
  } catch (error) {
    console.error('Fetch enums error:', error);
  }
};

onMounted(async () => {
  await loadEnums();
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
  filterCategory.value = '';
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
            <BaseIcon :path="mdiShieldCheckOutline" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            審計日誌列表
          </h3>

          <!-- 搜尋與按鈕 -->
          <div class="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2.5 sm:gap-3 w-full xl:w-auto justify-end">
            <!-- 類別過濾 -->
            <div class="flex items-center gap-2 w-full sm:w-auto flex-1 min-w-0">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0 whitespace-nowrap">類別</label>
              <div class="relative flex-1 sm:w-36 min-w-0">
                <select 
                  v-model="filterCategory"
                  class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm truncate cursor-pointer"
                  @change="handleSearch"
                >
                  <option value="">全部</option>
                  <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">
                    {{ cat.label }}
                  </option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                  <BaseIcon :path="mdiChevronDown" w="16" h="16" size="16" />
                </div>
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
                  <option value="success">成功</option>
                  <option value="failure">失敗</option>
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
