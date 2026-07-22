<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import {
  mdiPlus,
  mdiRefresh,
  mdiViewGridOutline,
  mdiDownload,
  mdiUpload,
  mdiCog
} from '@mdi/js';
import * as XLSX from 'xlsx';

import AgGridView2 from '@/components/AgGridView2.vue';
import ElDialogCustom from '@/components/ElDialogCustom.vue';
import { GridOptions } from 'ag-grid-community';
import { useMtrStore } from '@/store/useMtrStore';

const mtrStore = useMtrStore();

const registerGroupMap = computed(() => {
  const map: Record<string, string> = {};
  mtrStore.registerGroups.forEach(g => {
    map[g.value] = g.label;
  });
  return map;
});

import {
  getModbusRegisters,
  createModbusRegister,
  updateModbusRegister,
  deleteModbusRegister,
  getConfigsByType,
  writeInitialValuesToPlc,
  writeSettingValuesToPlc
} from '@/utils/api';

const { TLSuccess, TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '暫存器設定' }
];

const gridOptions: GridOptions = {
  rowSelection: 'single',
  autoSizeStrategy: {
    type: 'fitGridWidth',
  }
};

const pagination = ref({
  number: 0,
  size: 100,
  totalElements: 0,
  totalPages: 0,
});

const gridColumns = ref([
  { headerName: '暫存器名稱', field: 'name', flex: 1.2, minWidth: 150 },
  { headerName: '描述', field: 'description', flex: 1.5, minWidth: 200},
  {
    headerName: '暫存器分組',
    field: 'registerGroup',
    flex: 1.0,
    cellRenderer: (p: any) => {
      return registerGroupMap.value[p.value] || p.value || '';
    },
    minWidth: 120
  },
  // { headerName: '暫存器位址', field: 'address', minWidth: 130, maxWidth: 130, },
  // {
  //   headerName: '暫存器類型',
  //   field: 'registerType',
  //   cellRenderer: (p: any) => {
  //     const typeMap: Record<string, string> = {
  //       holding_register: 'Holding',
  //       input_register: 'Input',
  //       coil: 'Coil',
  //       discrete_input: 'Discrete',
  //     };
  //     return typeMap[p.value] || p.value || '';
  //   },
  //   minWidth: 130
  // },
  // { headerName: '資料型別', field: 'dataType', flex: 0.6, minWidth: 130 },
  // { headerName: '縮放比例', field: 'scale', flex: 0.5, minWidth: 130 },
  { headerName: '最新讀取值', field: 'value', flex: 1.0, minWidth: 120 },
  { headerName: '單位', field: 'unit', flex: 0.8, minWidth: 100 },
  {
    headerName: '啟用狀態',
    field: 'isActive',
    flex: 0.9,
    cellRenderer: (p: any) => {
      const active = p.value;
      return active 
        ? `<span class="px-2.5 py-1 rounded-full text-xs font-bold shadow-xs inline-block bg-emerald-50 text-emerald-700 border border-emerald-200/50">已啟用</span>`
        : `<span class="px-2.5 py-1 rounded-full text-xs font-bold shadow-xs inline-block bg-slate-100 text-slate-500 border border-slate-200/50">停用中</span>`;
    },
    minWidth: 110
  },

  {
    headerName: '操作',
    field: 'actions',
    cellRenderer: 'AGActionButtonRenderer',
    actionButtons: [
      { label: '編輯', event: 'edit', icon: 'mdiPencil', iconOnly: true },
      { label: '刪除', event: 'delete', icon: 'mdiDelete', iconOnly: true }
    ]
  }
]);

const onGridActionClick = ({ action, data }: any) => {
  if (action.event === 'edit') {
    openEditModal(data);
  } else if (action.event === 'delete') {
    deleteRegister(data);
  }
};

const handlePaginationChange = ({ page, pageSize }: { page: number; pageSize: number }) => {
  pagination.value.number = page;
  pagination.value.size = pageSize;
  fetchRegisters();
};

interface RegisterItem {
  id: number;
  deviceCode: string;
  address: number;
  name: string;
  registerType: string;
  dataType: string;
  scale: number;
  unit?: string;
  value?: string;
  description?: string;
  isActive: boolean;
  registerGroup: string;
}

const registers = ref<RegisterItem[]>([]);
const total = ref(0);
const loading = ref(false);

// Filters
const filterRegisterGroup = ref('');

const deviceOptions = ref<{ value: string; label: string }[]>([]);

const allDeviceOptions = computed(() => {
  const seen = new Set();
  const res: { value: string; label: string }[] = [];
  
  deviceOptions.value.forEach(opt => {
    if (!seen.has(opt.value)) {
      seen.add(opt.value);
      res.push(opt);
    }
  });
  return res;
});

const fetchDevices = async () => {
  try {
    const res = await getConfigsByType('MTR_PARAMS');
    if (res && res.data && res.data.configContent) {
      const content = JSON.parse(res.data.configContent);
      const options: { value: string; label: string }[] = [];
      if (content.leftItems && Array.isArray(content.leftItems)) {
        content.leftItems.forEach((item: any) => {
          if (item.code && item.code.startsWith('plc-data')) {
            const label = item.name ? `${item.name} (${item.code})` : item.code;
            options.push({ value: item.code, label });
          }
        });
      }
      if (content.rightItems && Array.isArray(content.rightItems)) {
        content.rightItems.forEach((item: any) => {
          if (item.code && item.code.startsWith('plc-data')) {
            const label = item.name ? `${item.name} (${item.code})` : item.code;
            options.push({ value: item.code, label });
          }
        });
      }
      deviceOptions.value = options;
    }
  } catch (error) {
    console.error('Failed to load MTR_PARAMS for devices:', error);
  }
};

const fetchRegisters = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      propertyName: 'sensorCode',
      order: 'ASC'
    };
    if (filterRegisterGroup.value) {
      params.registerGroup = filterRegisterGroup.value;
    }

    const res = await getModbusRegisters(params);
    if (res && res.data) {
      const list = res.data.source || [];
      registers.value = list.map((item: any) => ({
        ...item,
        name: item.sensorCode,
        description: item.sensorName,
        unit: item.sensorUnit,
        value: item.sensorValue
      }));
      const totalCount = res.data.total || 0;
      total.value = totalCount;
      pagination.value.totalElements = totalCount;
      pagination.value.totalPages = Math.ceil(totalCount / pagination.value.size);
    }
  } catch (error) {
    console.error('Fetch registers error:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await mtrStore.loadConfig();
  await fetchDevices();
  await fetchRegisters();
});

const handleSearch = () => {
  pagination.value.number = 0;
  fetchRegisters();
};

const handleReset = () => {
  filterRegisterGroup.value = '';
  pagination.value.number = 0;
  fetchRegisters();
};

// Modal configuration
const showModal = ref(false);
const isEdit = ref(false);
const modalTitle = ref('');

const formId = ref<number | null>(null);
const formDeviceCode = ref('');
const formAddress = ref<number | null>(0);
const formName = ref('');
const formRegisterType = ref('holding_register');
const formDataType = ref('int16');
const formScale = ref<number | null>(1.0);
const formUnit = ref('');
const formDescription = ref('');
const formIsActive = ref(true);
const formRegisterGroup = ref('realtime');
const formValue = ref('');


const openCreateModal = () => {
  isEdit.value = false;
  modalTitle.value = '新增暫存器設定';
  formId.value = null;
  formDeviceCode.value = allDeviceOptions.value.length > 0 ? allDeviceOptions.value[0].value : 'plc-data-1';
  formAddress.value = 0;
  formName.value = '';
  formRegisterType.value = 'holding_register';
  formDataType.value = 'int16';
  formScale.value = 1.0;
  formUnit.value = '';
  formDescription.value = '';
  formIsActive.value = true;
  formRegisterGroup.value = 'realtime';
  formValue.value = '';
  showModal.value = true;
};

const openEditModal = (item: RegisterItem) => {
  isEdit.value = true;
  modalTitle.value = '編輯暫存器設定';
  formId.value = item.id;
  formDeviceCode.value = item.deviceCode;
  formAddress.value = item.address;
  formName.value = item.name;
  formRegisterType.value = item.registerType || 'holding_register';
  formDataType.value = item.dataType || 'int16';
  formScale.value = item.scale !== undefined ? item.scale : 1.0;
  formUnit.value = item.unit || '';
  formDescription.value = item.description || '';
  formIsActive.value = item.isActive !== undefined ? item.isActive : true;
  formRegisterGroup.value = item.registerGroup || 'realtime';
  formValue.value = item.value || '';
  showModal.value = true;
};

const handleModalClose = async (dialogRef: any) => {
  if (dialogRef.close == true || dialogRef.success == false) {
    showModal.value = false;
    dialogRef.close = false;
    dialogRef.success = false;
    return;
  }

  // if (!formDeviceCode.value) {
  //   TLError('請選擇設備代碼');
  //   return;
  // }
  if (!formName.value.trim()) {
    TLError('暫存器名稱不能為空');
    return;
  }
  if (formAddress.value === null || formAddress.value === undefined || formAddress.value < 0) {
    TLError('暫存器位址必須為大於或等於 0 的整數');
    return;
  }
  if (!formRegisterType.value) {
    TLError('請選擇暫存器類型');
    return;
  }
  if (!formDataType.value) {
    TLError('請選擇資料型別');
    return;
  }
  if (formScale.value === null || formScale.value === undefined || isNaN(formScale.value)) {
    TLError('請輸入有效的縮放比例');
    return;
  }

  try {
    const payload = {
      deviceCode: formDeviceCode.value,
      address: parseInt(formAddress.value.toString()),
      sensorCode: formName.value.trim(),
      registerType: formRegisterType.value,
      dataType: formDataType.value,
      scale: parseFloat(formScale.value.toString()),
      sensorUnit: formUnit.value.trim() || null,
      sensorName: formDescription.value.trim() || null,
      isActive: formIsActive.value,
      registerGroup: formRegisterGroup.value,
      sensorValue: formValue.value.trim() || null
    };

    if (isEdit.value && formId.value !== null) {
      await updateModbusRegister(formId.value, payload);
      TLSuccess('更新暫存器設定成功');
    } else {
      await createModbusRegister(payload);
      TLSuccess('新增暫存器設定成功');
    }
    showModal.value = false;
    dialogRef.success = false;
    fetchRegisters();
  } catch (error: any) {
    console.error('Save register error:', error);
    TLError(error.response?.data?.message || '操作失敗，請重試');
  }
};

const deleteRegister = async (item: RegisterItem) => {
  if (confirm(`確定要刪除暫存器 [${item.name}] (位址: ${item.address}) 嗎？`)) {
    try {
      await deleteModbusRegister(item.id);
      TLSuccess('刪除暫存器設定成功');
      fetchRegisters();
    } catch (error: any) {
      console.error('Delete register error:', error);
      TLError(error.response?.data?.message || '刪除失敗');
    }
  }
};

const dataTypeMap: Record<string, string> = {
  int16: '16位元有號整數 (int16)',
  uint16: '16位元無號整數 (uint16)',
  int32: '32位元有號整數 (int32)',
  uint32: '32位元無號整數 (uint32)',
  float32: '32位元浮點數 (float32)',
  bool: '布林值 (bool)',
  bitmap: '位元遮罩 (bitmap)',
};

const handleExport = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: 0,
      pageSize: 100000,
      propertyName: 'id',
      order: 'ASC'
    };
    if (filterRegisterGroup.value) {
      params.registerGroup = filterRegisterGroup.value;
    }

    const res = await getModbusRegisters(params);
    if (!res || !res.data || !res.data.source) {
      TLError('無法取得暫存器資料以進行匯出');
      return;
    }

    const list = res.data.source || [];
    
    const typeMap: Record<string, string> = {
      holding_register: 'Holding Register',
      input_register: 'Input Register',
      coil: 'Coil',
      discrete_input: 'Discrete Input',
    };

    const dataRows = list.map((item: any) => ({
      '暫存器名稱 (sensorCode)': item.sensorCode,
      '描述 (sensorName)': item.sensorName || '',
      '暫存器分組': registerGroupMap.value[item.registerGroup] || item.registerGroup || '',
      '暫存器位址': item.address,
      '暫存器類型': typeMap[item.registerType] || item.registerType || '',
      '資料型別': dataTypeMap[item.dataType] || item.dataType || '',
      '縮放比例': item.scale !== undefined ? item.scale : 1.0,
      '最新讀取值': item.sensorValue || '',
      '單位': item.sensorUnit || '',
      '啟用狀態': item.isActive ? '已啟用' : '停用中',
    }));

    const worksheet = XLSX.utils.json_to_sheet(dataRows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Sensors');

    const wbout = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([wbout], { type: 'application/octet-stream' });
    const filename = `sensors_export_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    TLSuccess('匯出 Excel 成功');
  } catch (error) {
    console.error('Export error:', error);
    TLError('匯出失敗，請稍後重試');
  } finally {
    loading.value = false;
  }
};

const handleWriteInitialValues = async () => {
  if (!confirm('確定要將資料庫中的「初始值」寫入 PLC 嗎？')) return;
  loading.value = true;
  try {
    const res = await writeInitialValuesToPlc();
    if (res && res.success) {
      TLSuccess(res.message || '寫入 PLC 初始值成功');
    } else {
      TLError(res?.message || '寫入 PLC 初始值失敗');
    }
  } catch (error: any) {
    console.error('Write initial values error:', error);
    TLError(error.response?.data?.message || '寫入失敗，請稍後重試');
  } finally {
    loading.value = false;
  }
};

const handleWriteSettingValues = async () => {
  if (!confirm('確定要將資料庫中的「設定值」寫入 PLC 嗎？')) return;
  loading.value = true;
  try {
    const res = await writeSettingValuesToPlc();
    if (res && res.success) {
      TLSuccess(res.message || '寫入 PLC 設定值成功');
    } else {
      TLError(res?.message || '寫入 PLC 設定值失敗');
    }
  } catch (error: any) {
    console.error('Write setting values error:', error);
    TLError(error.response?.data?.message || '寫入失敗，請稍後重試');
  } finally {
    loading.value = false;
  }
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
        <div class="flex flex-col md:flex-row justify-between items-center gap-4 bg-white rounded-2xl p-4 shadow-xs">
          <!-- 表格頂端標題 -->
          <h3 class="text-slate-800 font-extrabold text-lg flex items-center gap-2 mb-0 shrink-0">
            <BaseIcon :path="mdiViewGridOutline" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            暫存器設定列表
          </h3>

          <!-- 搜尋與按鈕 -->
          <div class="flex flex-wrap items-center gap-4 w-full md:w-auto justify-end">
            <div class="flex items-center gap-2">
              <label class="text-xs font-bold text-slate-500 shrink-0 mb-0">暫存器分組</label>
              <div class="relative w-40">
                <select 
                  v-model="filterRegisterGroup"
                  class="w-full px-3 py-1.5 pl-8 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none"
                  @change="handleSearch"
                >
                  <option value="">全部群組</option>
                  <option v-for="g in mtrStore.registerGroups" :key="g.value" :value="g.value">
                    {{ g.label }}
                  </option>
                </select>
                <BaseIcon :path="mdiViewGridOutline" w="16" h="16" size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            </div>
            
            <BaseButton 
              @click="handleReset"
              colorClass="bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 shadow-xs px-4 py-1.5 rounded-lg text-sm"
              :icon="mdiRefresh"
            >
              重置
            </BaseButton>
            <!-- <BaseButton 
              @click="handleExport"
              colorClass="bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm px-4 py-1.5 rounded-lg text-sm"
              :icon="mdiDownload"
            >
              匯出表格
            </BaseButton> -->
            <BaseButton 
              @click="handleWriteInitialValues"
              colorClass="bg-amber-600 text-white hover:bg-amber-700 shadow-sm px-4 py-1.5 rounded-lg text-sm"
              :icon="mdiUpload"
            >
              寫入 PLC 初始值
            </BaseButton>
            <!-- <BaseButton 
              @click="handleWriteSettingValues"
              colorClass="bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm px-4 py-1.5 rounded-lg text-sm"
              :icon="mdiCog"
            >
              寫入 PLC 設定值
            </BaseButton> -->
            <BaseButton 
              @click="openCreateModal"
              colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm px-4 py-1.5 rounded-lg text-sm"
              :icon="mdiPlus"
            >
              新增暫存器
            </BaseButton>
          </div>
        </div>

        <!-- 數據表格 -->
        <div class="h-[calc(100vh-220px)] min-h-[220px]">
          <AgGridView2
            :options="gridOptions"
            :columns="gridColumns"
            :records="registers"
            :pagination="pagination"
            @grid-action-click="onGridActionClick"
            @pagination-change="handlePaginationChange"
          />
        </div>
      </div>

    </div>

    <!-- 新增 / 修改彈窗 -->
    <ElDialogCustom
      :title="modalTitle"
      :visible="showModal"
      width="650px"
      cancel="取消"
      action="確定儲存"
      @on-before-close="handleModalClose"
    >
      <div class="p-2 space-y-4 max-h-[70vh] overflow-y-auto">
        <div class="grid grid-cols-2 gap-4">
          <!-- 暫存器名稱 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              暫存器名稱 <span class="text-red-500">*</span>
            </label>
            <input 
              v-model="formName" 
              type="text" 
              placeholder="例如: highSpeedPress" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 暫存器位址 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              暫存器位址 (0-based) <span class="text-red-500">*</span>
            </label>
            <input 
              v-model="formAddress" 
              type="number" 
              min="0"
              placeholder="例如: 3200" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 暫存器類型 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              暫存器類型 <span class="text-red-500">*</span>
            </label>
            <select 
              v-model="formRegisterType"
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all"
            >
              <option value="holding_register">Holding Register</option>
              <option value="input_register">Input Register</option>
              <!-- <option value="coil">Coil</option>
              <option value="discrete_input"></option> -->
            </select>
          </div>

          <!-- 暫存器分組 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              暫存器分組 <span class="text-red-500">*</span>
            </label>
            <select 
              v-model="formRegisterGroup"
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all"
            >
              <option v-for="g in mtrStore.registerGroups" :key="g.value" :value="g.value">
                {{ g.label }}
              </option>
            </select>
          </div>

          <!-- 資料型別 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              資料型別 <span class="text-red-500">*</span>
            </label>
            <select 
              v-model="formDataType"
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all"
            >
              <option v-for="(label, key) in dataTypeMap" :key="key" :value="key">
                {{ label }}
              </option>
            </select>
          </div>

          <!-- 縮放比例 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              縮放比例 <span class="text-red-500">*</span>
            </label>
            <input 
              v-model="formScale" 
              type="number" 
              step="0.0001"
              placeholder="例如: 1.0 或 0.1" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 單位 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              單位 (選填)
            </label>
            <input 
              v-model="formUnit" 
              type="text" 
              placeholder="例如: °C, kPa" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 最新讀取值 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              最新讀取值 (選填)
            </label>
            <input 
              v-model="formValue" 
              type="text" 
              placeholder="例如: 250" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 描述 -->
          <div class="flex flex-col gap-1.5 col-span-2">
            <label class="text-sm font-bold text-slate-600">
              描述說明 (選填)
            </label>
            <input 
              v-model="formDescription" 
              type="text" 
              placeholder="暫存器的用途或備註" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 是否啟用 -->
          <div class="flex items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100 col-span-2">
            <input 
              id="formIsActive"
              v-model="formIsActive" 
              type="checkbox"
              class="w-4 h-4 rounded text-[#2a7eb5] border-slate-300 focus:ring-[#2a7eb5] cursor-pointer"
            />
            <label for="formIsActive" class="text-sm font-bold text-slate-600 cursor-pointer select-none">
              啟用此暫存器監控 (若不啟用，系統排程將不會讀取此暫存器值)
            </label>
          </div>
        </div>
      </div>
    </ElDialogCustom>

  </div>
</template>
