<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import {
  mdiRefresh,
  mdiHistory
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
    minWidth: 180,
    format: 'datetime'
  },
  {
    headerName: '暫存器名稱',
    field: 'name',
    flex: 1.5,
    minWidth: 180
  },
  {
    headerName: '讀取值',
    field: 'value',
    flex: 1.2,
    minWidth: 140,
    cellRenderer: (p: any) => {
      return `<span class="font-mono font-bold text-slate-800">${p.value}</span>`;
    }
  },
  {
    headerName: '暫存器 ID',
    field: 'registerId',
    flex: 1.0,
    minWidth: 120
  }
]);

const records = ref([]);
const loading = ref(false);

// Filters
const filterRegisterId = ref<number | string>('');
const registersOptions = ref<any[]>([]);

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
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      propertyName: 'recordedAt',
      order: 'DESC'
    };
    if (filterRegisterId.value !== '') {
      params.sensorCode = filterRegisterId.value;
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
  <div class="w-full pb-24 sm:pb-8">
    
    <!-- Breadcrumb -->
    <div class="w-full mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <!-- 內容區 -->
    <div class="w-full max-w-[1600px] mx-auto space-y-6">

      <!-- 資料表與操作 -->
      <div class="space-y-4">
        
        <!-- 表格頂端標題與搜尋條件一排 -->
        <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-white rounded-2xl p-4 shadow-xs">
          <!-- 表格頂端標題 -->
          <h3 class="text-slate-800 font-extrabold text-lg flex items-center gap-2 mb-0 shrink-0">
            <BaseIcon :path="mdiHistory" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            歷史資料查詢
          </h3>

          <!-- 搜尋與按鈕 -->
          <div class="flex flex-wrap items-center gap-4 w-full lg:w-auto justify-end">
            <!-- 暫存器過濾 -->
            <div class="flex items-center gap-2">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0">暫存器</label>
              <div class="relative w-64">
                <select 
                  v-model="filterRegisterId"
                  class="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm"
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
              </div>
            </div>
            
            <BaseButton 
              @click="handleReset"
              colorClass="bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 shadow-xs px-4 py-1.5 rounded-lg text-sm font-bold"
              :icon="mdiRefresh"
            >
              重置
            </BaseButton>
          </div>
        </div>

        <!-- 數據表格 -->
        <div class="h-[calc(100vh-220px)] min-h-[280px]">
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
